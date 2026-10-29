"""元数据发现与详情：自建移植 TMDB / 豆瓣的「出海报墙 + 详情」子集。

启停与 TMDB Key 读自内置插件配置；出站代理读偏好里的网络代理。
不做识别/刮削/资源搜索。
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.integrations import douban as douban_api
from app.integrations import tmdb as tmdb_api
from app.services import meta_image, plugins, preferences

_SOURCES = frozenset({"themoviedb", "douban"})
_KINDS = frozenset({"movie", "tv"})


def _proxy(user_id: str) -> str | None:
    prefs = preferences.get(user_id)
    proxy = prefs.network.proxy
    if proxy.enabled and proxy.host.strip():
        return proxy.host.strip()
    return None


def _require_source(source: str) -> str:
    if source not in _SOURCES:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "不支持的元数据源")
    return source


def _require_kind(kind: str) -> str:
    if kind not in _KINDS:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "类型只能是 movie 或 tv")
    return kind


def _ensure_enabled(user_id: str, plugin_id: str) -> schemas.PluginConfigView:
    config = plugins.get_config(user_id, plugin_id)
    if not config.enabled:
        raise ApiError(400, ErrorCode.PROVIDER_NOT_READY, f"{plugin_id} 插件已停用，请先在插件管理中启用")
    return config


def _year_of(text: object) -> int | None:
    raw = str(text or "").strip()
    if len(raw) >= 4 and raw[:4].isdigit():
        year = int(raw[:4])
        return year if 1800 <= year <= 2100 else None
    return None


def _tmdb_card(item: dict[str, Any], kind: str) -> schemas.MetaCardView:
    media_kind = kind
    if item.get("media_type") in ("movie", "tv"):
        media_kind = str(item["media_type"])
    title = str(item.get("title") or item.get("name") or "").strip() or "未命名"
    original = item.get("original_title") or item.get("original_name")
    date = item.get("release_date") or item.get("first_air_date") or ""
    rating = item.get("vote_average")
    return schemas.MetaCardView(
        source="themoviedb",
        id=str(item.get("id") or ""),
        kind=media_kind,
        title=title,
        originalTitle=str(original).strip() if original else None,
        year=_year_of(date),
        posterUrl=tmdb_api.poster_url(item.get("poster_path")),
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        overview=str(item.get("overview") or "").strip() or None,
    )


def _douban_card(item: dict[str, Any], kind: str) -> schemas.MetaCardView | None:
    subject = item.get("subject") if isinstance(item.get("subject"), dict) else item
    if not isinstance(subject, dict):
        return None
    media_id = str(subject.get("id") or "").strip()
    if not media_id:
        return None
    title = str(subject.get("title") or subject.get("name") or "").strip() or "未命名"
    original = subject.get("original_title") or subject.get("original_name")
    year = subject.get("year")
    rating_blob = subject.get("rating") if isinstance(subject.get("rating"), dict) else {}
    rating = rating_blob.get("value")
    card_kind = kind
    type_name = str(subject.get("type") or subject.get("subtype") or "").lower()
    if "tv" in type_name or "剧" in type_name:
        card_kind = "tv"
    elif "movie" in type_name or "电影" in type_name:
        card_kind = "movie"
    return schemas.MetaCardView(
        source="douban",
        id=media_id,
        kind=card_kind,
        title=title,
        originalTitle=str(original).strip() if original else None,
        year=int(year) if isinstance(year, int) else _year_of(year),
        posterUrl=meta_image.proxied_poster_url(douban_api.cover_url(subject), list_size=True),
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        overview=str(subject.get("card_subtitle") or subject.get("intro") or "").strip() or None,
    )


def _tmdb_items_from_payload(payload: dict[str, Any], default_kind: str) -> list[schemas.MetaCardView]:
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    items: list[schemas.MetaCardView] = []
    for row in results:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        items.append(_tmdb_card(row, default_kind))
    return items


def _douban_items_from_payload(
    payload: dict[str, Any], default_kind: str
) -> list[schemas.MetaCardView]:
    subject_rows = payload.get("subject_collection_items") or payload.get("items") or []
    if not isinstance(subject_rows, list):
        return []
    items: list[schemas.MetaCardView] = []
    for row in subject_rows:
        if not isinstance(row, dict):
            continue
        card = _douban_card(row, default_kind)
        if card:
            items.append(card)
    return items


def _tmdb_client(user_id: str) -> tmdb_api.TmdbClient:
    config = _ensure_enabled(user_id, "themoviedb")
    if not config.apiKey:
        raise ApiError(400, ErrorCode.PROVIDER_NOT_READY, "请先在插件管理中填写 TMDB API Key")
    return tmdb_api.TmdbClient(config.apiKey, proxy=_proxy(user_id))


def discover(
    user_id: str,
    *,
    source: str,
    kind: str,
    page: int = 1,
    category: str = "",
) -> schemas.MetaDiscoverResponse:
    source = _require_source(source)
    kind = _require_kind(kind)
    page = max(int(page or 1), 1)
    cat = (category or "").strip() or ("trending" if source == "themoviedb" else "hot")
    proxy = _proxy(user_id)

    if source == "themoviedb":
        client = _tmdb_client(user_id)
        try:
            if cat in {"popular", "hot"}:
                payload = client.popular(kind, page=page)
            elif cat in {"now_playing", "showing"} and kind == "movie":
                payload = client.now_playing(page=page)
            else:
                payload = client.trending(kind, page=page)
                cat = "trending"
        except tmdb_api.TmdbTransportError as exc:
            code = ErrorCode.PROVIDER_NOT_READY if exc.unauthorized else ErrorCode.UPSTREAM_ERROR
            raise ApiError(502 if not exc.unauthorized else 400, code, str(exc)) from exc
        items = _tmdb_items_from_payload(payload, kind)
        total_pages = int(payload.get("total_pages") or page)
        return schemas.MetaDiscoverResponse(
            source=source,
            kind=kind,
            category=cat,
            page=page,
            items=items,
            hasMore=page < total_pages,
        )

    _ensure_enabled(user_id, "douban")
    start = (page - 1) * 20
    client = douban_api.DoubanClient(proxy=proxy)
    try:
        if cat in {"showing", "now_playing"} and kind == "movie":
            payload = client.showing(start=start, count=20)
            cat = "showing"
        else:
            payload = client.hot(kind, start=start, count=20)
            cat = "hot"
    except douban_api.DoubanTransportError as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc)) from exc
    items = _douban_items_from_payload(payload, kind)
    total = payload.get("total")
    has_more = isinstance(total, int) and start + len(items) < total
    if not isinstance(total, int):
        has_more = len(items) >= 20
    return schemas.MetaDiscoverResponse(
        source=source,
        kind=kind,
        category=cat,
        page=page,
        items=items,
        hasMore=has_more,
    )


def _safe_board(
    board_id: str,
    title: str,
    group: str,
    source: str,
    loader: Any,
) -> schemas.MetaBoardView:
    try:
        items = loader()
        return schemas.MetaBoardView(
            id=board_id, title=title, group=group, source=source, items=items
        )
    except ApiError as exc:
        return schemas.MetaBoardView(
            id=board_id,
            title=title,
            group=group,
            source=source,
            items=[],
            message=exc.message,
        )
    except (tmdb_api.TmdbTransportError, douban_api.DoubanTransportError) as exc:
        return schemas.MetaBoardView(
            id=board_id,
            title=title,
            group=group,
            source=source,
            items=[],
            message=str(exc),
        )


def boards(user_id: str) -> schemas.MetaBoardsResponse:
    """推荐首页：对齐 MoviePilot 的分栏横滑榜单（可用源才拉）。"""
    proxy = _proxy(user_id)
    out: list[schemas.MetaBoardView] = []

    def tmdb_trending_all() -> list[schemas.MetaCardView]:
        client = _tmdb_client(user_id)
        return _tmdb_items_from_payload(client.trending_all(page=1), "movie")

    def tmdb_hot_movies() -> list[schemas.MetaCardView]:
        client = _tmdb_client(user_id)
        return _tmdb_items_from_payload(client.popular("movie", page=1), "movie")

    def tmdb_hot_tvs() -> list[schemas.MetaCardView]:
        client = _tmdb_client(user_id)
        return _tmdb_items_from_payload(client.popular("tv", page=1), "tv")

    def douban_showing() -> list[schemas.MetaCardView]:
        _ensure_enabled(user_id, "douban")
        return _douban_items_from_payload(
            douban_api.DoubanClient(proxy=proxy).showing(count=20), "movie"
        )

    def douban_movie_hot() -> list[schemas.MetaCardView]:
        _ensure_enabled(user_id, "douban")
        return _douban_items_from_payload(
            douban_api.DoubanClient(proxy=proxy).hot("movie", count=20), "movie"
        )

    def douban_tv_hot() -> list[schemas.MetaCardView]:
        _ensure_enabled(user_id, "douban")
        return _douban_items_from_payload(
            douban_api.DoubanClient(proxy=proxy).hot("tv", count=20), "tv"
        )

    def douban_anime() -> list[schemas.MetaCardView]:
        _ensure_enabled(user_id, "douban")
        return _douban_items_from_payload(
            douban_api.DoubanClient(proxy=proxy).animation(count=20), "tv"
        )

    # 并行拉取各榜：串行时豆瓣+TMDB 会把首页拖到数秒
    specs: list[tuple[str, str, str, str, Callable[[], list[schemas.MetaCardView]]]] = [
        ("tmdb_trending", "流行趋势", "ranking", "themoviedb", tmdb_trending_all),
        ("douban_showing", "正在热映", "movie", "douban", douban_showing),
        ("tmdb_movies", "热门电影", "movie", "themoviedb", tmdb_hot_movies),
        ("tmdb_tvs", "热门剧集", "tv", "themoviedb", tmdb_hot_tvs),
        ("douban_movie_hot", "豆瓣热门电影", "movie", "douban", douban_movie_hot),
        ("douban_tv_hot", "豆瓣热门剧集", "tv", "douban", douban_tv_hot),
        ("douban_anime", "热门动漫", "anime", "douban", douban_anime),
    ]
    results: dict[str, schemas.MetaBoardView] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(specs))) as pool:
        futures = {
            pool.submit(_safe_board, bid, title, group, source, loader): bid
            for bid, title, group, source, loader in specs
        }
        for fut in as_completed(futures):
            board = fut.result()
            results[board.id] = board
    out = [results[bid] for bid, *_ in specs if bid in results]

    # 全空且都是配置问题：抬一个明确错误，方便前端引导填 Key
    if all(not board.items for board in out) and any("API Key" in board.message for board in out):
        raise ApiError(400, ErrorCode.PROVIDER_NOT_READY, "请先在插件管理中填写 TMDB API Key")

    return schemas.MetaBoardsResponse(boards=[b for b in out if b.items or b.message])


def _tmdb_detail(user_id: str, kind: str, media_id: str) -> schemas.MetaDetailView:
    config = _ensure_enabled(user_id, "themoviedb")
    if not config.apiKey:
        raise ApiError(400, ErrorCode.PROVIDER_NOT_READY, "请先在插件管理中填写 TMDB API Key")
    try:
        payload = tmdb_api.TmdbClient(config.apiKey, proxy=_proxy(user_id)).detail(kind, media_id)
    except tmdb_api.TmdbTransportError as exc:
        code = ErrorCode.PROVIDER_NOT_READY if exc.unauthorized else ErrorCode.UPSTREAM_ERROR
        raise ApiError(502 if not exc.unauthorized else 400, code, str(exc)) from exc
    if not payload.get("id"):
        raise ApiError(404, ErrorCode.NOT_FOUND, "未找到该条目")

    title = str(payload.get("title") or payload.get("name") or "").strip() or "未命名"
    original = payload.get("original_title") or payload.get("original_name")
    date = payload.get("release_date") or payload.get("first_air_date") or ""
    genres = [
        str(g.get("name"))
        for g in (payload.get("genres") or [])
        if isinstance(g, dict) and g.get("name")
    ]
    runtime = payload.get("runtime")
    if kind == "tv" and isinstance(payload.get("episode_run_time"), list) and payload["episode_run_time"]:
        runtime = payload["episode_run_time"][0]
    credits = payload.get("credits") if isinstance(payload.get("credits"), dict) else {}
    cast_rows = credits.get("cast") if isinstance(credits.get("cast"), list) else []
    cast: list[schemas.MetaPersonView] = []
    for person in cast_rows[:12]:
        if not isinstance(person, dict) or not person.get("name"):
            continue
        cast.append(
            schemas.MetaPersonView(
                id=str(person.get("id") or ""),
                name=str(person["name"]),
                character=str(person.get("character") or ""),
                profileUrl=tmdb_api.poster_url(person.get("profile_path"), size="w185"),
            )
        )
    rating = payload.get("vote_average")
    homepage = payload.get("homepage")
    return schemas.MetaDetailView(
        source="themoviedb",
        id=str(payload["id"]),
        kind=kind,
        title=title,
        originalTitle=str(original).strip() if original else None,
        year=_year_of(date),
        posterUrl=tmdb_api.poster_url(payload.get("poster_path")),
        backdropUrl=tmdb_api.backdrop_url(payload.get("backdrop_path")),
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        overview=str(payload.get("overview") or "").strip() or None,
        genres=genres,
        runtimeMinutes=int(runtime) if isinstance(runtime, (int, float)) else None,
        cast=cast,
        homepage=str(homepage).strip() if homepage else None,
    )


def _douban_detail(user_id: str, kind: str, media_id: str) -> schemas.MetaDetailView:
    _ensure_enabled(user_id, "douban")
    client = douban_api.DoubanClient(proxy=_proxy(user_id))
    try:
        payload = client.detail(kind, media_id)
    except douban_api.DoubanTransportError as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc)) from exc
    if not payload.get("id"):
        # 豆瓣 movie/tv 端点偶发类型错位，试另一侧
        alt = "tv" if kind == "movie" else "movie"
        try:
            payload = client.detail(alt, media_id)
            kind = alt
        except douban_api.DoubanTransportError:
            raise ApiError(404, ErrorCode.NOT_FOUND, "未找到该条目") from None
        if not payload.get("id"):
            raise ApiError(404, ErrorCode.NOT_FOUND, "未找到该条目")

    title = str(payload.get("title") or "").strip() or "未命名"
    original = payload.get("original_title")
    rating_blob = payload.get("rating") if isinstance(payload.get("rating"), dict) else {}
    rating = rating_blob.get("value")
    genres = [str(g) for g in (payload.get("genres") or []) if g]
    runtime = None
    durations = payload.get("durations")
    if isinstance(durations, list) and durations:
        digits = "".join(ch for ch in str(durations[0]) if ch.isdigit())
        runtime = int(digits) if digits else None

    cast: list[schemas.MetaPersonView] = []
    try:
        celeb = client.celebrities(kind, media_id)
    except douban_api.DoubanTransportError:
        celeb = {}
    actors = celeb.get("actors") if isinstance(celeb.get("actors"), list) else []
    for person in actors[:12]:
        if not isinstance(person, dict) or not person.get("name"):
            continue
        roles = person.get("roles") if isinstance(person.get("roles"), list) else []
        cast.append(
            schemas.MetaPersonView(
                id=str(person.get("id") or ""),
                name=str(person["name"]),
                character=" / ".join(str(r) for r in roles if r),
                profileUrl=meta_image.proxied_poster_url(
                    douban_api.cover_url(
                        person.get("avatar") if isinstance(person.get("avatar"), dict) else person
                    ),
                    list_size=True,
                ),
            )
        )

    return schemas.MetaDetailView(
        source="douban",
        id=str(payload["id"]),
        kind=kind,
        title=title,
        originalTitle=str(original).strip() if original else None,
        year=_year_of(payload.get("year")),
        posterUrl=meta_image.proxied_poster_url(douban_api.cover_url(payload), list_size=False),
        backdropUrl=None,
        rating=float(rating) if isinstance(rating, (int, float)) else None,
        overview=str(payload.get("intro") or "").strip() or None,
        genres=genres,
        runtimeMinutes=runtime,
        cast=cast,
        homepage=f"https://movie.douban.com/subject/{payload['id']}/",
    )


def detail(user_id: str, *, source: str, media_id: str, kind: str) -> schemas.MetaDetailView:
    source = _require_source(source)
    kind = _require_kind(kind)
    media_id = media_id.strip()
    if not media_id:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "缺少条目 ID")
    if source == "themoviedb":
        return _tmdb_detail(user_id, kind, media_id)
    return _douban_detail(user_id, kind, media_id)
