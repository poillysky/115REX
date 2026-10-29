"""站点配置（对齐 MoviePilot 站点管理核心能力）。

账号级；按域名唯一。支持导入、连通测试、统计、批量优先级。
资源浏览 / CookieCloud / 站点用户数据依赖索引器插件，本阶段不做。
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.storage.db import SessionLocal
from app.storage.models import Site, SiteStatistic
from app.services import moviepilot, site_spider


def _user_pk(user_id: str) -> int:
    try:
        return int(user_id.removeprefix("u-"))
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc


def _normalize_domain(domain: str, url: str) -> str:
    value = (domain or "").strip().lower()
    if value:
        return value.removeprefix("www.")
    host = urlparse((url or "").strip()).hostname or ""
    return host.lower().removeprefix("www.")


def _normalize_note(note: object) -> str:
    if note is None:
        return ""
    if isinstance(note, str):
        return note
    try:
        return json.dumps(note, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(note)


def _as_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _as_int(value: object, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _view(row: Site) -> schemas.SiteView:
    return schemas.SiteView(
        id=row.id,
        name=row.name,
        domain=row.domain,
        url=row.url,
        pri=row.pri,
        rss=row.rss or "",
        cookie=row.cookie or "",
        apikey=row.apikey or "",
        token=row.token or "",
        ua=row.ua or "",
        proxy=bool(row.proxy),
        filter=row.filter or "",
        render=bool(row.render),
        public=bool(row.public),
        note=row.note or "",
        timeout=row.timeout or 15,
        downloader=row.downloader or "",
        limitInterval=int(getattr(row, "limit_interval", 0) or 0),
        limitCount=int(getattr(row, "limit_count", 0) or 0),
        limitSeconds=int(getattr(row, "limit_seconds", 0) or 0),
        isActive=bool(row.is_active),
    )


def _stat_view(row: SiteStatistic) -> schemas.SiteStatisticView:
    return schemas.SiteStatisticView(
        domain=row.domain,
        success=row.success,
        fail=row.fail,
        seconds=row.seconds,
        lstState=row.lst_state,
        lstModAt=row.lst_mod_at,
        lstModDate=row.lst_mod_date or "",
        note=row.note or "",
    )


# 耗时记录最多保留条数（对齐 MoviePilot 统计详情的展示量级）
_TIME_RECORD_KEEP = 20


def _append_time_record(note: str, stamp: str, seconds: int) -> str:
    """把本次耗时追加进 JSON 文本记录，只保留最近 _TIME_RECORD_KEEP 条。"""
    try:
        records = json.loads(note) if note else {}
        if not isinstance(records, dict):
            records = {}
    except (TypeError, ValueError):
        records = {}
    records[stamp] = seconds
    if len(records) > _TIME_RECORD_KEEP:
        keep = sorted(records)[-_TIME_RECORD_KEEP:]
        records = {key: records[key] for key in keep}
    return json.dumps(records, ensure_ascii=False)


def _apply_write(row: Site, payload: schemas.SiteWrite, *, set_domain: bool) -> None:
    url = payload.url.strip()
    domain = _normalize_domain(payload.domain, url)
    if not url or not domain:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "站点地址不能为空")
    # 名称由前端留空时回落到域名，用户只需填站点地址
    name = payload.name.strip() or domain
    if set_domain:
        row.domain = domain
    row.name = name
    row.url = url
    row.pri = int(payload.pri or 0)
    row.rss = (payload.rss or "").strip()
    row.cookie = payload.cookie or ""
    row.apikey = (payload.apikey or "").strip()
    row.token = (payload.token or "").strip()
    row.ua = (payload.ua or "").strip()
    row.proxy = bool(payload.proxy)
    row.filter = (payload.filter or "").strip()
    row.render = bool(payload.render)
    row.public = bool(payload.public)
    row.note = _normalize_note(payload.note)
    row.timeout = max(1, int(payload.timeout or 15))
    row.downloader = (payload.downloader or "").strip()
    row.limit_interval = max(0, int(payload.limitInterval or 0))
    row.limit_count = max(0, int(payload.limitCount or 0))
    row.limit_seconds = max(0, int(payload.limitSeconds or 0))
    row.is_active = bool(payload.isActive)


def _refresh_providers(user_pk: int) -> None:
    """站点变更后重建该账号的站点源，避免搜索读到旧 Cookie 或已删站点。

    放在函数内 import：providers 依赖 services，模块级互相引用会成环。
    """
    from app.providers import site_provider

    site_provider.rebuild(user_pk)


def list_sites(user_id: str) -> schemas.SiteListView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        rows = (
            db.query(Site)
            .filter(Site.user_id == pk)
            .order_by(Site.pri.asc(), Site.name.asc(), Site.id.asc())
            .all()
        )
        return schemas.SiteListView(sites=[_view(row) for row in rows])


def get_site(user_id: str, site_id: int) -> schemas.SiteView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        return _view(_require(db, pk, site_id))


def create_site(user_id: str, payload: schemas.SiteWrite) -> schemas.SiteView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        domain = _normalize_domain(payload.domain, payload.url)
        exists = (
            db.query(Site).filter(Site.user_id == pk, Site.domain == domain).one_or_none()
        )
        if exists:
            raise ApiError(409, ErrorCode.BAD_REQUEST, f"域名「{domain}」已存在")
        row = Site(user_id=pk)
        _apply_write(row, payload, set_domain=True)
        db.add(row)
        db.commit()
        db.refresh(row)
        view = _view(row)
    _refresh_providers(pk)
    return view


def update_site(user_id: str, site_id: int, payload: schemas.SiteWrite) -> schemas.SiteView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        row = _require(db, pk, site_id)
        _apply_write(row, payload, set_domain=False)
        db.commit()
        db.refresh(row)
        view = _view(row)
    _refresh_providers(pk)
    return view


def patch_site(user_id: str, site_id: int, payload: schemas.SitePatch) -> schemas.SiteView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        row = _require(db, pk, site_id)
        data = payload.model_dump(exclude_unset=True)
        mapping = {
            "name": "name",
            "url": "url",
            "pri": "pri",
            "rss": "rss",
            "cookie": "cookie",
            "apikey": "apikey",
            "token": "token",
            "ua": "ua",
            "proxy": "proxy",
            "filter": "filter",
            "render": "render",
            "public": "public",
            "note": "note",
            "timeout": "timeout",
            "downloader": "downloader",
            "limitInterval": "limit_interval",
            "limitCount": "limit_count",
            "limitSeconds": "limit_seconds",
            "isActive": "is_active",
        }
        for key, attr in mapping.items():
            if key not in data or data[key] is None:
                continue
            value = data[key]
            if attr in {"name", "url"}:
                text = str(value).strip()
                if not text:
                    raise ApiError(400, ErrorCode.BAD_REQUEST, "站点名称与地址不能为空")
                setattr(row, attr, text)
            elif attr in {"proxy", "render", "public", "is_active"}:
                setattr(row, attr, bool(value))
            elif attr in {"pri", "timeout", "limit_interval", "limit_count", "limit_seconds"}:
                setattr(row, attr, max(0 if attr != "timeout" else 1, int(value)))
            elif attr == "note":
                setattr(row, attr, _normalize_note(value))
            else:
                setattr(row, attr, str(value))
        db.commit()
        db.refresh(row)
        view = _view(row)
    _refresh_providers(pk)
    return view


def delete_site(user_id: str, site_id: int) -> None:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        row = _require(db, pk, site_id)
        domain = row.domain
        db.delete(row)
        stat = (
            db.query(SiteStatistic)
            .filter(SiteStatistic.user_id == pk, SiteStatistic.domain == domain)
            .one_or_none()
        )
        if stat:
            db.delete(stat)
        db.commit()
    _refresh_providers(pk)


def update_priorities(user_id: str, items: list[schemas.SitePriorityItem]) -> schemas.SiteListView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        for item in items:
            row = (
                db.query(Site)
                .filter(Site.user_id == pk, Site.id == item.id)
                .one_or_none()
            )
            if row:
                row.pri = int(item.pri)
        db.commit()
    return list_sites(user_id)


def list_statistics(user_id: str) -> schemas.SiteStatisticListView:
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        rows = db.query(SiteStatistic).filter(SiteStatistic.user_id == pk).all()
        return schemas.SiteStatisticListView(stats=[_stat_view(row) for row in rows])


def get_statistic(user_id: str, domain: str) -> schemas.SiteStatisticView:
    """单站点统计。没测过时返回全零，前端按 unknown 展示。"""
    pk = _user_pk(user_id)
    value = (domain or "").strip().lower().removeprefix("www.")
    with SessionLocal() as db:
        row = (
            db.query(SiteStatistic)
            .filter(SiteStatistic.user_id == pk, SiteStatistic.domain == value)
            .one_or_none()
        )
        if not row:
            return schemas.SiteStatisticView(domain=value)
        return _stat_view(row)


def _clean_cookie(raw: str) -> str:
    """规整用户从浏览器复制的 Cookie。

    常见脏数据：带 `Cookie: ` 前缀、带换行或制表符、键值之间逗号分隔。
    httpx 不接受换行，NexusPHP 也不认多出来的前缀，都会直接判成未登录。
    """
    value = (raw or "").strip()
    if value.lower().startswith("cookie:"):
        value = value[7:]
    value = re.sub(r"[\r\n\t]+", " ", value).strip()
    # 浏览器 DevTools 复制出来常是逗号分隔，Cookie 头要求分号
    if ";" not in value and "," in value:
        value = value.replace(",", ";")
    return value.strip().rstrip(";")


def test_site(user_id: str, site_id: int) -> schemas.SiteTestResultView:
    """探测站点首页连通性，并写入统计。"""
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        row = _require(db, pk, site_id)
        url = row.url
        cookie = _clean_cookie(row.cookie or "")
        ua = row.ua or "Mozilla/5.0 (compatible; 115REX/0.1)"
        timeout = max(3, min(int(row.timeout or 15), 60))
        public = bool(row.public)
        domain = row.domain

    headers = {"User-Agent": ua}
    if cookie:
        headers["Cookie"] = cookie

    started = time.perf_counter()
    ok = False
    message = ""
    html = ""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
        elapsed = time.perf_counter() - started
        html = response.text
        # 私有站：状态码正常不代表 Cookie 有效，必须确认页面处于登录态
        if not public and response.status_code < 400 and not site_spider.is_logged_in(html):
            ok = False
            message = "Cookie 已失效" if response.status_code == 200 else f"HTTP {response.status_code}"
        else:
            ok = 200 <= response.status_code < 500
            message = f"HTTP {response.status_code}"
    except httpx.TimeoutException:
        elapsed = time.perf_counter() - started
        message = "连接超时"
    except httpx.HTTPError as exc:
        elapsed = time.perf_counter() - started
        message = str(exc) or "请求失败"

    seconds = max(0, int(round(elapsed)))
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with SessionLocal() as db:
        stat = (
            db.query(SiteStatistic)
            .filter(SiteStatistic.user_id == pk, SiteStatistic.domain == domain)
            .one_or_none()
        )
        if not stat:
            stat = SiteStatistic(user_id=pk, domain=domain)
            db.add(stat)
        if ok:
            stat.success = int(stat.success or 0) + 1
            stat.lst_state = 0
        else:
            stat.fail = int(stat.fail or 0) + 1
            stat.lst_state = 1
        stat.seconds = seconds
        stat.lst_mod_at = int(time.time())
        stat.lst_mod_date = stamp
        stat.note = _append_time_record(stat.note or "", stamp, seconds)
        db.commit()
        db.refresh(stat)
        view = _stat_view(stat)

    return schemas.SiteTestResultView(
        ok=ok,
        seconds=round(elapsed, 2),
        message=message if ok else message or "连通失败",
        statistic=view,
    )


_PASSKEY_MASK = re.compile(r"(passkey=)[0-9a-zA-Z]+", re.I)


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
# NexusPHP 系站点的标题形如「车站 - Powered by NexusPHP」「站点 :: 登录」，取第一个分隔符前的内容
_TITLE_SPLIT_RE = re.compile(r"\s*(?:[-|–—:：]{1,3}|::)\s*")


def _site_name_from_title(title: str) -> str:
    text = re.sub(r"\s+", " ", title).strip()
    if not text:
        return ""
    return _TITLE_SPLIT_RE.split(text, maxsplit=1)[0].strip()


def fetch_site_meta(
    url: str, ua: str = "", timeout: float = 10.0, proxy: bool = False
) -> schemas.SiteMetaView:
    """抓站点首页 title 取站名。失败不报错，前端回落到域名。

    proxy 与站点「使用代理访问」开关一致：开则显式跟随系统代理；
    关则用 None，让 httpx 走默认行为（同样会读系统/环境变量代理），
    不能传 False——那会**主动禁用**系统代理，反而让本机代理环境里的站点连不通。
    """
    target = (url or "").strip()
    if not target.startswith(("http://", "https://")):
        target = f"https://{target}" if target else ""
    if not target:
        return schemas.SiteMetaView(message="站点地址为空")

    domain = _normalize_domain("", target)
    headers = {"User-Agent": ua or "Mozilla/5.0 (compatible; 115REX/0.1)"}
    try:
        response = httpx.get(
            target,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            trust_env=True if proxy else None,
        )
        title = _TITLE_RE.search(response.text)
    except httpx.HTTPError as exc:
        return schemas.SiteMetaView(domain=domain, message=str(exc) or "请求失败")

    name = _site_name_from_title(title.group(1)) if title else ""
    return schemas.SiteMetaView(
        name=name or domain, domain=domain, message="" if name else "未取到站点标题"
    )


def _mask_passkey(url: str) -> str:
    """探测结果要回显给前端，passkey 等同于账号凭据，必须打码。"""
    return _PASSKEY_MASK.sub(r"\1***", url)


def _promo_from_factors(upload: float, download: float) -> str | None:
    """把 MoviePilot 的上传/下载系数翻译成站点上的促销叫法。"""
    if download == 0 and upload >= 2:
        return "2X 免费"
    if download == 0:
        return "免费"
    if download < 1 and upload >= 2:
        return f"{round(download * 100)}% 下载 2X"
    if download < 1:
        return f"{round(download * 100)}% 下载"
    if upload >= 2:
        return "2X"
    if upload > 1:
        return f"{round(upload, 1)}X"
    return None


def _sample_from_moviepilot(item: moviepilot.MoviePilotTorrent) -> schemas.SiteProbeSampleView:
    return schemas.SiteProbeSampleView(
        torrentId=_id_from_url(item.page_url or item.enclosure),
        title=item.title,
        subtitle=item.subtitle,
        sizeBytes=item.size_bytes,
        resolution=site_spider.parse_resolution(item.title),
        seeders=item.seeders,
        category=item.category,
        snatched=item.grabs,
        promo=_promo_from_factors(item.upload_factor, item.download_factor),
        promoUntil=item.free_until,
        hitAndRun=item.hit_and_run,
        downloadUrl=_mask_passkey(item.enclosure),
    )


def _id_from_url(url: str) -> str:
    match = re.search(r"[?&]id=(\d+)", url)
    return match.group(1) if match else ""


def _probe_via_moviepilot(
    keyword: str, site_name: str, site_url: str
) -> schemas.SiteProbeResultView:
    """让 MoviePilot 搜全站，再按站点名挑出这个站的结果。"""
    started = time.perf_counter()
    try:
        # MoviePilot 的站点名与本服务的站点名可能不一致，两个都拿去匹配
        torrents = moviepilot.search_title(keyword, [site_name, _site_name_from_title(site_name)])
    except moviepilot.MoviePilotError as exc:
        return schemas.SiteProbeResultView(ok=False, message=str(exc), url=site_url)

    samples = [_sample_from_moviepilot(item) for item in torrents[:20]]
    return schemas.SiteProbeResultView(
        ok=bool(torrents),
        message=(
            f"MoviePilot 命中 {len(torrents)} 条" if torrents else "MoviePilot 没有返回这个站的种子"
        ),
        seconds=round(time.perf_counter() - started, 2),
        url=site_url,
        matched=len(torrents),
        samples=samples,
    )


async def probe_site(user_id: str, site_id: int, keyword: str) -> schemas.SiteProbeResultView:
    """用关键词真搜一次，回报解析出的条数与样例，供用户确认站点可用。"""
    pk = _user_pk(user_id)
    with SessionLocal() as db:
        row = _require(db, pk, site_id)
        url = (row.url or "").strip()
        name = (row.name or "").strip() or (row.domain or "").strip()
        cookie = (row.cookie or "").strip()
        ua = (row.ua or "").strip() or "Mozilla/5.0 (compatible; 115REX/0.1)"
        proxy = bool(row.proxy)
        timeout = max(3, min(int(row.timeout or 15), 60))

    # 配了 MoviePilot 就全交给它：站点页面的反爬、Cookie 维护都由它处理
    if moviepilot.is_configured():
        return await asyncio.to_thread(_probe_via_moviepilot, keyword, name, url)

    if not url:
        return schemas.SiteProbeResultView(ok=False, message="站点地址为空")
    if not public and not cookie:
        return schemas.SiteProbeResultView(ok=False, message="请先填写 Cookie，私有站未登录无法搜索")

    search_url = site_spider.build_search_url(url, keyword)
    headers = {"User-Agent": ua}
    if cookie:
        headers["Cookie"] = cookie

    started = time.perf_counter()
    # 跨境站点握手经常 5~15 秒、偶发丢包，连接超时给足；读超时沿用站点配置
    limits = httpx.Timeout(float(timeout), connect=15.0)
    response: httpx.Response | None = None
    last_error: Exception | None = None
    # 一次抖动就报「超时」体验太差，最多尝试 3 次，仅在网络层失败时重试
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(
                timeout=limits,
                follow_redirects=True,
                # 同 fetch_site_meta：关代理开关时传 None，不要传 False
                trust_env=True if proxy else None,
            ) as client:
                response = await client.get(search_url, headers=headers)
            break
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))

    if response is None:
        elapsed = round(time.perf_counter() - started, 2)
        message = "请求超时" if isinstance(last_error, httpx.TimeoutException) else str(last_error)
        return schemas.SiteProbeResultView(
            ok=False, message=f"{message}（已重试 3 次）", seconds=elapsed, url=search_url
        )
    html = response.text

    elapsed = round(time.perf_counter() - started, 2)
    if response.status_code != 200:
        return schemas.SiteProbeResultView(
            ok=False, message=f"HTTP {response.status_code}", seconds=elapsed, url=search_url
        )
    # 未登录时 NexusPHP 会 302 到 login.php，跟随后是登录页，解析必然为空
    if "login.php" in str(response.url) or "takelogin" in html[:4000]:
        return schemas.SiteProbeResultView(
            ok=False, message="Cookie 已失效，被重定向到登录页", seconds=elapsed, url=search_url
        )

    torrents = site_spider.parse_torrent_list(html, url)
    # 探测只为核对解析结果，取前 20 条即可；再多的内容留给正式搜索流程
    samples = [
        schemas.SiteProbeSampleView(
            torrentId=item.torrent_id,
            title=item.title,
            subtitle=item.subtitle,
            sizeBytes=item.size_bytes,
            resolution=site_spider.parse_resolution(item.title),
            seeders=item.seeders,
            category=item.category,
            snatched=item.snatched,
            promo=item.promo,
            promoUntil=item.promo_until,
            hitAndRun=item.hit_and_run,
            sticky=item.sticky,
            bonus=item.bonus,
            downloadUrl=_mask_passkey(item.download_url or item.magnet or ""),
        )
        for item in torrents[:20]
    ]
    return schemas.SiteProbeResultView(
        ok=bool(torrents),
        message=f"解析到 {len(torrents)} 条" if torrents else "页面可访问，但没解析到种子行",
        seconds=elapsed,
        url=search_url,
        matched=len(torrents),
        samples=samples,
    )


def _require(db: Session, user_pk: int, site_id: int) -> Site:
    row = db.query(Site).filter(Site.user_id == user_pk, Site.id == site_id).one_or_none()
    if not row:
        raise ApiError(404, ErrorCode.NOT_FOUND, "站点不存在")
    return row


def site_write_from_import(raw: dict) -> schemas.SiteWrite:
    """兼容 MoviePilot 导出 JSON（snake_case）与本契约 camelCase。"""

    def pick(*keys: str, default: object = "") -> object:
        for key in keys:
            if key in raw and raw[key] is not None:
                return raw[key]
        return default

    name = str(pick("name", default="") or "").strip()
    url = str(pick("url", default="") or "").strip()
    domain = str(pick("domain", default="") or "").strip()
    return schemas.SiteWrite(
        name=name,
        domain=domain,
        url=url,
        pri=_as_int(pick("pri", default=0), 0),
        rss=str(pick("rss", default="") or ""),
        cookie=str(pick("cookie", default="") or ""),
        apikey=str(pick("apikey", "apiKey", default="") or ""),
        token=str(pick("token", default="") or ""),
        ua=str(pick("ua", default="") or ""),
        proxy=_as_bool(pick("proxy", default=False)),
        filter=str(pick("filter", default="") or ""),
        render=_as_bool(pick("render", default=False)),
        public=_as_bool(pick("public", default=False)),
        note=_normalize_note(pick("note", default="")),
        timeout=_as_int(pick("timeout", default=15), 15),
        downloader=str(pick("downloader", default="") or ""),
        limitInterval=_as_int(pick("limitInterval", "limit_interval", default=0), 0),
        limitCount=_as_int(pick("limitCount", "limit_count", default=0), 0),
        limitSeconds=_as_int(pick("limitSeconds", "limit_seconds", default=0), 0),
        isActive=_as_bool(pick("isActive", "is_active", default=True), default=True),
    )
