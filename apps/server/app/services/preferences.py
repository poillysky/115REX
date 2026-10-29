"""偏好服务（docs/07 §2.8）。账号级，Web 与 App 共享，落库在 `preferences` 表。

嵌套结构（图标库、代理、GitHub、高级参数、插件）按 JSON 文本存进两列，
读取时整体还原成 PreferencesView，写入时整体序列化——与接口「整段替换」的语义一致。
"""

from __future__ import annotations

import json
import secrets
from typing import Any
from urllib.parse import urljoin

import httpx
from sqlalchemy.orm import Session

from app.api import schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.storage.db import SessionLocal
from app.storage.models import Preference

# 内置图标库：Emby / Fileball 生态常见的 JSON 图标索引。用户可禁用或删改。
DEFAULT_ICON_LIBRARIES = [
    schemas.IconLibraryView(
        id="lige-emby",
        name="离歌图标库",
        url="https://raw.githubusercontent.com/lige47/QuanX-icon-rule/refs/heads/main/lige-emby-icon.json",
        enabled=True,
    ),
    schemas.IconLibraryView(
        id="tfel-emby",
        name="TFEL图标库",
        url="https://emby-icon.vercel.app/TFEL-Emby.json",
        enabled=True,
    ),
    schemas.IconLibraryView(
        id="sakura-yuan",
        name="白糖圆形图标库",
        url="https://raw.githubusercontent.com/baiitang/Sakura/main/Fileball/Yuan/tubiao.json",
        enabled=True,
    ),
    schemas.IconLibraryView(
        id="sakura-fang",
        name="白糖方形图标库",
        url="https://raw.githubusercontent.com/baiitang/Sakura/main/Fileball/Fang/tubiao.json",
        enabled=True,
    ),
]

# 内置过滤规则档位：与资源源筛选的严格程度一一对应。
FILTER_RULES = ("off", "basic", "strict")

# 插件市场的出厂值：settings 里还没有这一段时用它兜底
DEFAULT_PLUGIN_MARKETS = ["https://github.com/jxxghp/MoviePilot-Plugins"]


def _user_pk(user_id: str) -> int:
    """令牌里是 `u-<pk>`，这里还原成主键。"""
    try:
        return int(user_id.removeprefix("u-"))
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc


def _load(row: Preference) -> schemas.PreferencesView:
    """把一行记录还原成接口视图。JSON 列解析失败时按默认值兜，不让脏数据卡住整个页面。"""
    try:
        libraries = [schemas.IconLibraryView(**item) for item in json.loads(row.icon_libraries)]
    except (ValueError, TypeError):
        libraries = list(DEFAULT_ICON_LIBRARIES)
    try:
        settings: dict[str, Any] = json.loads(row.settings)
    except (ValueError, TypeError):
        settings = {}

    # 插件市场为空时给出厂值：老记录升级后不会变成「一个市场都没有」
    stored_plugins = settings.get("plugins") or {}
    plugins = schemas.PluginView(**stored_plugins)
    if not plugins.market:
        plugins = schemas.PluginView(market=list(DEFAULT_PLUGIN_MARKETS), autoReload=plugins.autoReload)

    return schemas.PreferencesView(
        defaultTargetDir=row.default_target_dir,
        defaultSubtitleLang=row.default_subtitle_lang,
        enabledProviders=json.loads(row.enabled_providers or "[]"),
        autoTransfer=row.auto_transfer,
        iconLibraries=libraries,
        apiToken=row.api_token,
        network=schemas.NetworkView(**settings.get("network", {})),
        basic=schemas.BasicView(**settings.get("basic", {})),
        github=schemas.GithubView(**settings.get("github", {})),
        advanced=schemas.AdvancedView(**settings.get("advanced", {})),
        plugins=plugins,
        qbittorrent=schemas.QbittorrentView(**settings.get("qbittorrent", {})),
        moviepilot=schemas.MoviepilotView(**settings.get("moviepilot", {})),
    )


def _open(db: Session, user_id: str) -> Preference:
    """取用户那一行；首次访问时按内置默认值建出来，API 令牌一并生成。"""
    pk = _user_pk(user_id)
    row = db.query(Preference).filter(Preference.user_id == pk).one_or_none()
    if row is None:
        row = Preference(
            user_id=pk,
            icon_libraries=json.dumps(
                [item.model_dump() for item in DEFAULT_ICON_LIBRARIES], ensure_ascii=False
            ),
            settings=json.dumps({}, ensure_ascii=False),
            api_token=secrets.token_hex(20),
        )
        db.add(row)
        db.flush()
    return row


def _store(row: Preference, view: schemas.PreferencesView) -> schemas.PreferencesView:
    """整行回写：先算出新的视图，再一次性序列化落库。"""
    row.default_target_dir = view.defaultTargetDir
    row.default_subtitle_lang = view.defaultSubtitleLang
    row.enabled_providers = json.dumps(view.enabledProviders, ensure_ascii=False)
    row.auto_transfer = view.autoTransfer
    row.icon_libraries = json.dumps(
        [item.model_dump() for item in view.iconLibraries], ensure_ascii=False
    )
    row.api_token = view.apiToken
    row.settings = json.dumps(
        {
            "network": view.network.model_dump(),
            "basic": view.basic.model_dump(),
            "github": view.github.model_dump(),
            "advanced": view.advanced.model_dump(),
            "plugins": view.plugins.model_dump(),
            "qbittorrent": view.qbittorrent.model_dump(),
            "moviepilot": view.moviepilot.model_dump(),
        },
        ensure_ascii=False,
    )
    return view


def get(user_id: str) -> schemas.PreferencesView:
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row)
        db.commit()
    return view


def update(user_id: str, payload: schemas.PreferencesUpdate) -> schemas.PreferencesView:
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(
            update={key: value for key, value in payload.model_dump().items() if value is not None}
        )
        _store(row, view)
        db.commit()
    return view


def save_icon_libraries(
    user_id: str, payload: schemas.IconLibrariesUpdate
) -> schemas.PreferencesView:
    """整表替换图标库。只接受 http(s) 地址，id 冲突时拒绝。"""
    rows: list[schemas.IconLibraryView] = []
    seen: set[str] = set()
    for item in payload.libraries:
        name = item.name.strip()
        url = item.url.strip()
        if not name:
            raise ApiError(400, ErrorCode.BAD_REQUEST, "图标库名称不能为空")
        if not url.startswith(("https://", "http://")):
            raise ApiError(400, ErrorCode.BAD_REQUEST, "图标库地址必须以 http(s) 开头")
        library_id = item.id or f"lib-{secrets.token_hex(4)}"
        if library_id in seen:
            raise ApiError(400, ErrorCode.BAD_REQUEST, "图标库 ID 重复")
        seen.add(library_id)
        rows.append(
            schemas.IconLibraryView(id=library_id, name=name, url=url, enabled=item.enabled)
        )
    with SessionLocal() as db:
        stored = _open(db, user_id)
        view = _load(stored).model_copy(update={"iconLibraries": rows})
        _store(stored, view)
        db.commit()
    return view


# Emby / Fileball 图标索引的常见形态：`{ 名称: 图片地址 }`，或带一层 `data` / `icons` 包裹。
_ICON_LIBRARY_CONTAINERS = ("data", "icons", "items")
_ICON_LIBRARY_MAX_ENTRIES = 2000
_ICON_LIBRARY_TIMEOUT = 8.0


def _icon_entries(payload: Any, base_url: str) -> list[schemas.IconLibraryEntryView]:
    """把图标索引摊平成「名称 → 绝对图片地址」，相对地址按索引自身的地址补齐。"""
    if isinstance(payload, dict):
        for key in _ICON_LIBRARY_CONTAINERS:
            nested = payload.get(key)
            if isinstance(nested, (dict, list)):
                return _icon_entries(nested, base_url)
        pairs = payload.items()
    elif isinstance(payload, list):
        pairs = (
            (str(item.get("name") or ""), item.get("url"))
            for item in payload
            if isinstance(item, dict)
        )
    else:
        return []

    entries: list[schemas.IconLibraryEntryView] = []
    for name, value in pairs:
        if isinstance(value, dict):
            value = value.get("url") or value.get("icon")
        if not isinstance(value, str) or not value.strip():
            continue
        entries.append(
            schemas.IconLibraryEntryView(
                name=str(name).strip() or "未命名", url=urljoin(base_url, value.strip())
            )
        )
        if len(entries) >= _ICON_LIBRARY_MAX_ENTRIES:
            break
    return entries


def fetch_icon_library(user_id: str, url: str) -> list[schemas.IconLibraryEntryView]:
    """抓取图标库索引。只允许用户自己配置过的地址，避免变成任意 URL 代理。"""
    target = url.strip()
    if not target.startswith(("https://", "http://")):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "图标库地址必须以 http(s) 开头")
    with SessionLocal() as db:
        allowed = {item.url for item in _load(_open(db, user_id)).iconLibraries}
    if target not in allowed:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "图标库不在已保存的列表中")

    try:
        # 出口走设置页的网络代理；trust_env=False 避免机器上的 HTTP_PROXY 环境变量干扰
        with httpx.Client(
            timeout=_ICON_LIBRARY_TIMEOUT,
            follow_redirects=True,
            trust_env=False,
            proxy=get_settings().storage_proxy.strip() or None,
        ) as client:
            response = client.get(target, headers={"User-Agent": "115REX"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "图标库读取失败，请检查地址是否可访问") from exc

    return _icon_entries(payload, target)


def save_network(user_id: str, payload: schemas.NetworkUpdate) -> schemas.PreferencesView:
    """整段替换出站代理。地址须带 scheme，避免把主机端口猜错。"""
    host = payload.proxy.host.strip()
    if not host:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "代理地址不能为空")
    if not host.startswith(("http://", "https://", "socks5://", "socks5h://")):
        raise ApiError(
            400, ErrorCode.BAD_REQUEST, "代理地址需以 http:// https:// socks5:// socks5h:// 开头"
        )
    proxy = schemas.ProxyView(enabled=payload.proxy.enabled, host=host)
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"network": schemas.NetworkView(proxy=proxy)})
        _store(row, view)
        db.commit()
    return view


def save_basic(user_id: str, payload: schemas.BasicUpdate) -> schemas.PreferencesView:
    """整段替换基础设定。过滤规则只接受内置档位，避免前端传进未知值。"""
    if payload.filterRule not in FILTER_RULES:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "过滤规则不在内置档位内")
    bridge_url = payload.bridgeUrl.strip()
    if bridge_url and not bridge_url.startswith(("https://", "http://")):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "反代地址必须以 http(s) 开头")
    basic = schemas.BasicView(
        lanUrl=payload.lanUrl.strip(),
        bridgeUrl=bridge_url,
        filterRule=payload.filterRule,
        doubanCache=payload.doubanCache,
        backgroundImage=payload.backgroundImage.strip(),
    )
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"basic": basic})
        _store(row, view)
        db.commit()
    return view


def save_github(user_id: str, payload: schemas.GithubUpdate) -> schemas.PreferencesView:
    """整段替换 GitHub 配置。镜像地址须带 scheme，令牌与账号去空白。"""
    proxy = payload.proxy.strip()
    if proxy and not proxy.startswith(("https://", "http://")):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "加速地址必须以 http(s) 开头")
    github = schemas.GithubView(proxy=proxy, token=payload.token.strip(), user=payload.user.strip())
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"github": github})
        _store(row, view)
        db.commit()
    return view


def save_advanced(user_id: str, payload: schemas.AdvancedUpdate) -> schemas.PreferencesView:
    """整段替换高级参数。超时与并发都限制在可用区间，防止填 0 或负数。"""
    if not 1 <= payload.requestTimeout <= 120:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "请求超时需在 1 到 120 秒之间")
    if not 1 <= payload.concurrency <= 64:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "并发数需在 1 到 64 之间")
    advanced = schemas.AdvancedView(
        requestTimeout=payload.requestTimeout, concurrency=payload.concurrency
    )
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"advanced": advanced})
        _store(row, view)
        db.commit()
    return view


def save_qbittorrent(
    user_id: str, payload: schemas.QbittorrentUpdate
) -> schemas.PreferencesView:
    """整段替换 qBittorrent 配置。启用时地址必填且须带 scheme，避免把主机端口猜错。"""
    url = payload.url.strip().rstrip("/")
    if payload.enabled and not url:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "qBittorrent 地址不能为空")
    if url and not url.startswith(("http://", "https://")):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "qBittorrent 地址需以 http(s):// 开头")
    qbittorrent = schemas.QbittorrentView(
        enabled=payload.enabled,
        url=url,
        username=payload.username.strip(),
        password=payload.password,
        category=payload.category.strip(),
        savePath=payload.savePath.strip(),
    )
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"qbittorrent": qbittorrent})
        _store(row, view)
        db.commit()
    return view


def get_qbittorrent(user_id: str) -> schemas.QbittorrentView:
    """给下载器客户端取当前用户的 qBittorrent 连接参数。"""
    with SessionLocal() as db:
        return _load(_open(db, user_id)).qbittorrent


def save_moviepilot(
    user_id: str, payload: schemas.MoviepilotUpdate
) -> schemas.PreferencesView:
    """整段替换 MoviePilot 配置。启用时地址必填，未写 scheme 时按 http 补全。"""
    url = payload.url.strip().rstrip("/")
    if url and not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    if payload.enabled and not url:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "MoviePilot 地址不能为空")
    moviepilot = schemas.MoviepilotView(
        enabled=payload.enabled,
        url=url,
        token=payload.token.strip(),
    )
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"moviepilot": moviepilot})
        _store(row, view)
        db.commit()
    return view


def get_moviepilot(user_id: str) -> schemas.MoviepilotView:
    """给 MoviePilot 客户端取当前的接入参数。"""
    with SessionLocal() as db:
        return _load(_open(db, user_id)).moviepilot


def save_token(user_id: str, payload: schemas.TokenUpdate) -> schemas.PreferencesView:
    """替换 API 令牌。只接受 40 位十六进制，与生成规则保持一致。"""
    token = payload.apiToken.strip().lower()
    if len(token) != 40 or any(c not in "0123456789abcdef" for c in token):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "API 令牌需为 40 位十六进制")
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"apiToken": token})
        _store(row, view)
        db.commit()
    return view


def save_plugins(user_id: str, payload: schemas.PluginUpdate) -> schemas.PreferencesView:
    """整段替换插件市场配置。空地址丢弃，非 http(s) 拒绝。"""
    markets: list[str] = []
    for raw in payload.market:
        url = raw.strip()
        if not url:
            continue
        if not url.startswith(("https://", "http://")):
            raise ApiError(400, ErrorCode.BAD_REQUEST, "插件市场地址必须以 http(s) 开头")
        if url not in markets:
            markets.append(url)
    plugins = schemas.PluginView(market=markets, autoReload=payload.autoReload)
    with SessionLocal() as db:
        row = _open(db, user_id)
        view = _load(row).model_copy(update={"plugins": plugins})
        _store(row, view)
        db.commit()
    return view
