"""偏好（docs/07 §2.8）。配置按账号落库，路由只负责取当前用户。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api import deps, schemas
from app.services import github_auth, moviepilot, preferences, qbittorrent

router = APIRouter(tags=["preferences"])


def _user_id(claim: deps.CurrentClaim) -> str:
    """偏好是账号级资源，用令牌里的 user_id，而不是设备。"""
    return str(claim.get("sub") or "")


@router.get("/preferences", response_model=schemas.PreferencesView)
def read_preferences(claim: deps.CurrentClaim) -> schemas.PreferencesView:
    return preferences.get(_user_id(claim))


@router.put("/preferences", response_model=schemas.PreferencesView)
def write_preferences(
    payload: schemas.PreferencesUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    return preferences.update(_user_id(claim), payload)


@router.put("/preferences/icon-libraries", response_model=schemas.PreferencesView)
def write_icon_libraries(
    payload: schemas.IconLibrariesUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整表替换图标库列表；列表顺序即生效优先级。"""
    return preferences.save_icon_libraries(_user_id(claim), payload)


@router.get(
    "/preferences/icon-libraries/icons", response_model=list[schemas.IconLibraryEntryView]
)
def read_icon_library_entries(
    url: str, claim: deps.CurrentClaim
) -> list[schemas.IconLibraryEntryView]:
    """抓取一个图标库的 JSON 索引，供客户端选择头像等图片。"""
    return preferences.fetch_icon_library(_user_id(claim), url)


@router.put("/preferences/network", response_model=schemas.PreferencesView)
def write_network(
    payload: schemas.NetworkUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整段替换网络代理设置，供转存与资源源出站使用。"""
    return preferences.save_network(_user_id(claim), payload)


@router.put("/preferences/basic", response_model=schemas.PreferencesView)
def write_basic(payload: schemas.BasicUpdate, claim: deps.CurrentClaim) -> schemas.PreferencesView:
    """整段替换基础设定：内网地址、桥接地址开关、过滤规则、豆瓣缓存、背景图。"""
    return preferences.save_basic(_user_id(claim), payload)


@router.put("/preferences/github", response_model=schemas.PreferencesView)
def write_github(
    payload: schemas.GithubUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整段替换 GitHub 配置：镜像加速、令牌、账号。"""
    return preferences.save_github(_user_id(claim), payload)


@router.put("/preferences/advanced", response_model=schemas.PreferencesView)
def write_advanced(
    payload: schemas.AdvancedUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整段替换高级参数：请求超时与并发。"""
    return preferences.save_advanced(_user_id(claim), payload)


@router.put("/preferences/qbittorrent", response_model=schemas.PreferencesView)
def write_qbittorrent(
    payload: schemas.QbittorrentUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整段替换 qBittorrent 下载器配置：地址、账号、默认分类与保存路径。"""
    return preferences.save_qbittorrent(_user_id(claim), payload)


@router.post("/preferences/qbittorrent/test", response_model=schemas.QbittorrentTestResultView)
async def test_qbittorrent(
    payload: schemas.QbittorrentUpdate, claim: deps.CurrentClaim
) -> schemas.QbittorrentTestResultView:
    """用当前表单里填的值试连一次，不落库。便于保存前先确认地址与账号。"""
    return await qbittorrent.test_connection(payload)


@router.put("/preferences/moviepilot", response_model=schemas.PreferencesView)
def write_moviepilot(
    payload: schemas.MoviepilotUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整段替换 MoviePilot 接入配置：地址与令牌。"""
    return preferences.save_moviepilot(_user_id(claim), payload)


@router.get("/preferences/moviepilot/status", response_model=schemas.MoviepilotStatusView)
async def read_moviepilot_status(claim: deps.CurrentClaim) -> schemas.MoviepilotStatusView:
    """读 MoviePilot 与它名下下载器的运行概况，只查询不改动对方流程。"""
    return await moviepilot.read_status(preferences.get_moviepilot(_user_id(claim)))


@router.post("/preferences/moviepilot/test", response_model=schemas.MoviepilotStatusView)
async def test_moviepilot(
    payload: schemas.MoviepilotUpdate, claim: deps.CurrentClaim
) -> schemas.MoviepilotStatusView:
    """用表单里填的值试连一次，不落库。"""
    return await moviepilot.read_status(
        schemas.MoviepilotView(enabled=payload.enabled, url=payload.url, token=payload.token)
    )


@router.put("/preferences/token", response_model=schemas.PreferencesView)
def write_token(payload: schemas.TokenUpdate, claim: deps.CurrentClaim) -> schemas.PreferencesView:
    """替换 API 令牌：外部客户端调用控制面时使用。"""
    return preferences.save_token(_user_id(claim), payload)


@router.put("/preferences/plugins", response_model=schemas.PreferencesView)
def write_plugins(
    payload: schemas.PluginUpdate, claim: deps.CurrentClaim
) -> schemas.PreferencesView:
    """整段替换插件市场配置。"""
    return preferences.save_plugins(_user_id(claim), payload)


# ---- GitHub 授权（设备码流程，docs/07 §2.8.1）。令牌原文与本组接口绝缘。


@router.get("/preferences/github/auth/status", response_model=schemas.GithubAuthStatusView)
def read_github_auth(claim: deps.CurrentClaim) -> schemas.GithubAuthStatusView:
    """授权状态摘要：是否已配置、是否仍有效、脱敏令牌。"""
    return github_auth.status(_user_id(claim))


@router.post("/preferences/github/auth/start", response_model=schemas.GithubDeviceAuthStartView)
def start_github_auth(claim: deps.CurrentClaim) -> schemas.GithubDeviceAuthStartView:
    """申请设备码，前端据此展示短码与验证地址。"""
    return github_auth.start_device_auth(_user_id(claim))


@router.post("/preferences/github/auth/poll", response_model=schemas.GithubDeviceAuthPollView)
def poll_github_auth(
    payload: schemas.GithubDeviceAuthPollRequest, claim: deps.CurrentClaim
) -> schemas.GithubDeviceAuthPollView:
    """轮询一次授权结果。前端按 retryAfter 秒后再来。"""
    return github_auth.poll_device_auth(_user_id(claim), payload.sessionId)


@router.post("/preferences/github/auth/manual", response_model=schemas.GithubAuthStatusView)
def write_github_manual_token(
    payload: schemas.GithubManualTokenRequest, claim: deps.CurrentClaim
) -> schemas.GithubAuthStatusView:
    """手动填写 PAT，作为设备码授权的兜底。"""
    return github_auth.set_manual_token(_user_id(claim), payload.token)


@router.delete("/preferences/github/auth/token", response_model=None)
def delete_github_token(claim: deps.CurrentClaim) -> None:
    """解除授权，清空令牌与 OAuth 元数据。"""
    github_auth.clear_token(_user_id(claim))
