"""内置元数据插件 + 市场已安装插件。

内置：bootstrap 宿主模块，Logo 由前端本地打包。
市场：安装时把图标下载到 data/plugin-icons；「已安装」只读本地 iconUrl，运行时不联网取图。
"""

from __future__ import annotations

import json
import secrets
from typing import Any

from sqlalchemy.orm import Session

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.services import plugin_icons, preferences
from app.storage.db import SessionLocal
from app.storage.models import Preference

# 出厂内置：优先最稳定的媒体识别源（MP 默认 SEARCH/RECOGNIZE/SCRAP = themoviedb）
_BUILTIN: tuple[schemas.PluginItemView, ...] = (
    schemas.PluginItemView(
        id="themoviedb",
        name="TMDB",
        author="TheMovieDb",
        version="1.0.0",
        description="全球影视元数据：搜索、识别、剧集与海报。作为默认识别与刮削源。",
        kind="mediarecognize",
        capability=["search", "recognize", "scrape", "discover"],
        builtin=True,
        installed=True,
        enabled=True,
        hasUpdate=False,
        homepage="https://www.themoviedb.org/",
        repoUrl="",
        labels=["电影", "剧集", "元数据"],
    ),
    schemas.PluginItemView(
        id="douban",
        name="豆瓣",
        author="Douban",
        version="1.0.0",
        description="中文片名搜索与识别、热门发现；适合国内片源标题匹配。",
        kind="mediarecognize",
        capability=["search", "recognize", "discover"],
        builtin=True,
        installed=True,
        enabled=True,
        hasUpdate=False,
        homepage="https://www.douban.com/",
        repoUrl="",
        labels=["中文", "电影", "剧集"],
    ),
    schemas.PluginItemView(
        id="bangumi",
        name="Bangumi",
        author="Bangumi",
        version="1.0.0",
        description="动画与番剧元数据：放送表、条目识别与搜索。",
        kind="mediarecognize",
        capability=["search", "recognize", "discover"],
        builtin=True,
        installed=True,
        enabled=True,
        hasUpdate=False,
        homepage="https://bgm.tv/",
        repoUrl="",
        labels=["动画", "番剧"],
    ),
    schemas.PluginItemView(
        id="fanart",
        name="Fanart",
        author="fanart.tv",
        version="1.0.0",
        description="海报 / 背景 / Logo 补图；依赖 TMDB（电影）或 TVDB（剧集）编号。",
        kind="other",
        capability=["images"],
        builtin=True,
        installed=True,
        enabled=True,
        hasUpdate=False,
        homepage="https://fanart.tv/",
        repoUrl="",
        labels=["海报", "图片"],
    ),
)

_BUILTIN_IDS = frozenset(item.id for item in _BUILTIN)


def _user_pk(user_id: str) -> int:
    try:
        return int(user_id.removeprefix("u-"))
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc


def _settings(row: Preference) -> dict[str, Any]:
    try:
        data = json.loads(row.settings or "{}")
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


def _states(settings: dict[str, Any]) -> dict[str, bool]:
    raw = settings.get("pluginStates") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, bool] = {}
    for key, value in raw.items():
        if isinstance(key, str):
            out[key] = bool(value)
    return out


def _configs(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = settings.get("pluginConfigs") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def _market_installed(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = settings.get("installedMarketPlugins") or {}
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def _api_key_of(configs: dict[str, dict[str, Any]], plugin_id: str) -> str:
    blob = configs.get(plugin_id) or {}
    key = blob.get("apiKey")
    return key.strip() if isinstance(key, str) else ""


def _open(db: Session, user_id: str) -> Preference:
    pk = _user_pk(user_id)
    row = db.query(Preference).filter(Preference.user_id == pk).one_or_none()
    if row is None:
        row = Preference(
            user_id=pk,
            icon_libraries="[]",
            settings="{}",
            api_token=secrets.token_hex(20),
        )
        db.add(row)
        db.flush()
    return row


def _network_proxy(user_id: str) -> str | None:
    prefs = preferences.get(user_id)
    proxy = prefs.network.proxy
    if proxy.enabled and proxy.host.strip():
        return proxy.host.strip()
    return None


def _local_icon_or_empty(plugin_id: str) -> str:
    return plugin_icons.local_icon_url(plugin_id) if plugin_icons.local_icon_path(plugin_id) else ""


def _builtin_item(item: schemas.PluginItemView, states: dict[str, bool]) -> schemas.PluginItemView:
    enabled = states[item.id] if item.id in states else item.enabled
    return item.model_copy(update={"enabled": bool(enabled), "installed": True, "builtin": True})


def _market_item(blob: dict[str, Any], states: dict[str, bool]) -> schemas.PluginItemView:
    plugin_id = str(blob.get("id") or "").strip()
    enabled = states[plugin_id] if plugin_id in states else bool(blob.get("enabled", True))
    caps = blob.get("capability") if isinstance(blob.get("capability"), list) else []
    labels = blob.get("labels") if isinstance(blob.get("labels"), list) else []
    return schemas.PluginItemView(
        id=plugin_id,
        name=str(blob.get("name") or plugin_id),
        author=str(blob.get("author") or ""),
        version=str(blob.get("version") or "1.0.0"),
        description=str(blob.get("description") or ""),
        kind=str(blob.get("kind") or "other"),
        capability=[str(c) for c in caps if c],
        builtin=False,
        installed=True,
        enabled=bool(enabled),
        hasUpdate=bool(blob.get("hasUpdate", False)),
        homepage=str(blob.get("homepage") or ""),
        repoUrl=str(blob.get("repoUrl") or ""),
        labels=[str(x) for x in labels if x],
        iconUrl=_local_icon_or_empty(plugin_id),
    )


def list_installed(user_id: str) -> schemas.PluginListView:
    with SessionLocal() as db:
        row = _open(db, user_id)
        settings = _settings(row)
        states = _states(settings)
        market = _market_installed(settings)
        db.commit()
    items = [_builtin_item(item, states) for item in _BUILTIN]
    for blob in market.values():
        items.append(_market_item(blob, states))
    return schemas.PluginListView(plugins=items)


def list_market(user_id: str) -> schemas.PluginListView:
    """插件库：仅第三方市场插件；内置只出现在「内置」。

    市场目录拉取待接入；当前返回空列表，前端展示海报墙空态。
    """
    _ = user_id
    return schemas.PluginListView(plugins=[])


def get_plugin(user_id: str, plugin_id: str) -> schemas.PluginItemView:
    with SessionLocal() as db:
        row = _open(db, user_id)
        settings = _settings(row)
        states = _states(settings)
        market = _market_installed(settings)
        db.commit()
    for item in _BUILTIN:
        if item.id == plugin_id:
            return _builtin_item(item, states)
    blob = market.get(plugin_id)
    if blob:
        return _market_item(blob, states)
    raise ApiError(404, ErrorCode.NOT_FOUND, "插件不存在")


def install_plugin(user_id: str, payload: schemas.PluginInstall) -> schemas.PluginItemView:
    """安装市场插件：元数据落库，远程图标立刻下载到本地。"""
    plugin_id = payload.id.strip()
    if not plugin_id:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "插件 id 不能为空")
    if plugin_id in _BUILTIN_IDS:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "内置插件无需安装")
    try:
        plugin_icons.safe_plugin_id(plugin_id)
    except ValueError as exc:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "插件 id 非法") from exc

    remote_icon = payload.iconUrl.strip()
    if remote_icon:
        try:
            plugin_icons.download_icon(
                plugin_id, remote_icon, proxy=_network_proxy(user_id)
            )
        except ValueError as exc:
            raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc)) from exc

    with SessionLocal() as db:
        row = _open(db, user_id)
        settings = _settings(row)
        market = _market_installed(settings)
        states = _states(settings)
        market[plugin_id] = {
            "id": plugin_id,
            "name": payload.name.strip() or plugin_id,
            "author": payload.author.strip(),
            "version": payload.version.strip() or "1.0.0",
            "description": payload.description.strip(),
            "kind": payload.kind.strip() or "other",
            "capability": list(payload.capability),
            "homepage": payload.homepage.strip(),
            "repoUrl": payload.repoUrl.strip(),
            "labels": list(payload.labels),
            "enabled": True,
        }
        states[plugin_id] = True
        settings["installedMarketPlugins"] = market
        settings["pluginStates"] = states
        row.settings = json.dumps(settings, ensure_ascii=False)
        db.commit()
        return _market_item(market[plugin_id], states)


def uninstall_plugin(user_id: str, plugin_id: str) -> None:
    if plugin_id in _BUILTIN_IDS:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "内置插件不能卸载")
    with SessionLocal() as db:
        row = _open(db, user_id)
        settings = _settings(row)
        market = _market_installed(settings)
        if plugin_id not in market:
            raise ApiError(404, ErrorCode.NOT_FOUND, "插件未安装")
        market.pop(plugin_id, None)
        states = _states(settings)
        states.pop(plugin_id, None)
        configs = _configs(settings)
        configs.pop(plugin_id, None)
        settings["installedMarketPlugins"] = market
        settings["pluginStates"] = states
        settings["pluginConfigs"] = configs
        row.settings = json.dumps(settings, ensure_ascii=False)
        db.commit()
    plugin_icons.remove_local_icon(plugin_id)


def patch_plugin(user_id: str, plugin_id: str, payload: schemas.PluginPatch) -> schemas.PluginItemView:
    if payload.enabled is None:
        return get_plugin(user_id, plugin_id)

    with SessionLocal() as db:
        row = _open(db, user_id)
        settings = _settings(row)
        states = _states(settings)
        market = _market_installed(settings)
        if plugin_id not in _BUILTIN_IDS and plugin_id not in market:
            raise ApiError(404, ErrorCode.NOT_FOUND, "插件不存在")
        states[plugin_id] = bool(payload.enabled)
        settings["pluginStates"] = states
        row.settings = json.dumps(settings, ensure_ascii=False)
        db.commit()
    return get_plugin(user_id, plugin_id)


def get_config(user_id: str, plugin_id: str) -> schemas.PluginConfigView:
    item = get_plugin(user_id, plugin_id)
    with SessionLocal() as db:
        row = _open(db, user_id)
        configs = _configs(_settings(row))
        db.commit()
    return schemas.PluginConfigView(enabled=item.enabled, apiKey=_api_key_of(configs, plugin_id))


def save_config(
    user_id: str, plugin_id: str, payload: schemas.PluginConfigUpdate
) -> schemas.PluginConfigView:
    # 确认存在
    get_plugin(user_id, plugin_id)

    with SessionLocal() as db:
        row = _open(db, user_id)
        settings = _settings(row)
        states = _states(settings)
        configs = _configs(settings)
        blob = dict(configs.get(plugin_id) or {})

        if payload.enabled is not None:
            states[plugin_id] = bool(payload.enabled)
            settings["pluginStates"] = states
        if payload.apiKey is not None:
            blob["apiKey"] = payload.apiKey.strip()
            configs[plugin_id] = blob
            settings["pluginConfigs"] = configs

        row.settings = json.dumps(settings, ensure_ascii=False)
        db.commit()
        return schemas.PluginConfigView(
            enabled=bool(states.get(plugin_id, True)),
            apiKey=_api_key_of(configs, plugin_id),
        )
