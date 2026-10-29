"""插件管理：内置 / 已安装 / 安装卸载；图标安装时落盘。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

from app.api import deps, schemas
from app.errors import ApiError, ErrorCode
from app.services import plugin_icons, plugins

router = APIRouter(prefix="/plugins", tags=["plugins"])


def _user_id(claim: deps.CurrentClaim) -> str:
    return str(claim.get("sub") or "")


@router.get("/installed", response_model=schemas.PluginListView)
def list_installed(claim: deps.CurrentClaim) -> schemas.PluginListView:
    return plugins.list_installed(_user_id(claim))


@router.get("/market", response_model=schemas.PluginListView)
def list_market(claim: deps.CurrentClaim) -> schemas.PluginListView:
    return plugins.list_market(_user_id(claim))


@router.post("/install", response_model=schemas.PluginItemView)
def install_plugin(
    payload: schemas.PluginInstall, claim: deps.CurrentClaim
) -> schemas.PluginItemView:
    return plugins.install_plugin(_user_id(claim), payload)


@router.get("/{plugin_id}/icon")
def plugin_icon(plugin_id: str) -> Response:
    """本地图标文件。供 <img> 直链，无需 Bearer（内容不敏感）。"""
    path = plugin_icons.local_icon_path(plugin_id)
    if path is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "图标不存在")
    return FileResponse(path, media_type=plugin_icons.media_type_for(path))


@router.get("/{plugin_id}", response_model=schemas.PluginItemView)
def get_plugin(plugin_id: str, claim: deps.CurrentClaim) -> schemas.PluginItemView:
    return plugins.get_plugin(_user_id(claim), plugin_id)


@router.patch("/{plugin_id}", response_model=schemas.PluginItemView)
def patch_plugin(
    plugin_id: str, payload: schemas.PluginPatch, claim: deps.CurrentClaim
) -> schemas.PluginItemView:
    return plugins.patch_plugin(_user_id(claim), plugin_id, payload)


@router.delete("/{plugin_id}", status_code=204)
def uninstall_plugin(plugin_id: str, claim: deps.CurrentClaim) -> Response:
    plugins.uninstall_plugin(_user_id(claim), plugin_id)
    return Response(status_code=204)


@router.get("/{plugin_id}/config", response_model=schemas.PluginConfigView)
def get_config(plugin_id: str, claim: deps.CurrentClaim) -> schemas.PluginConfigView:
    return plugins.get_config(_user_id(claim), plugin_id)


@router.put("/{plugin_id}/config", response_model=schemas.PluginConfigView)
def save_config(
    plugin_id: str, payload: schemas.PluginConfigUpdate, claim: deps.CurrentClaim
) -> schemas.PluginConfigView:
    return plugins.save_config(_user_id(claim), plugin_id, payload)
