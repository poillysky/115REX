"""GitHub 授权（docs/07 §2.8.1）。设备码流程的状态机，照 MoviePilot 的形态实现。

三段式：申请设备码 → 前端展示短码让用户去 GitHub 授权 → 前端按服务端给定的间隔轮询。
令牌与刷新元数据落 `github_auth` 表；对外一律只给脱敏摘要。
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field

from app.api import schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.integrations.github import (
    GithubAuthClient,
    GithubTransportError,
    TokenExchange,
)
from app.storage.db import SessionLocal
from app.storage.models import GithubAuth

# 轮询节流：GitHub 要求的最小间隔由服务端守，前端拿到的 retryAfter 以此为准
_POLL_PENDING = "authorization_pending"
_POLL_SLOW_DOWN = "slow_down"
_POLL_DENIED = "access_denied"
_POLL_EXPIRED = frozenset({"expired_token", "token_expired"})

# 离过期不足这么多秒就先刷新
_REFRESH_WINDOW = 60


@dataclass
class _PendingSession:
    """进程内设备授权会话，不保存任何用户令牌。重启即失效，用户重新点一次即可。"""

    device_code: str
    expires_at: float
    interval_seconds: int
    next_poll_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


_sessions: dict[str, _PendingSession] = {}
_sessions_lock = threading.Lock()


def _client_id() -> str:
    return get_settings().github_client_id.strip()


def _user_pk(user_id: str) -> int:
    try:
        return int(user_id.removeprefix("u-"))
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc


def _client() -> GithubAuthClient:
    """出站代理取偏好里的 GitHub 加速地址，与设置页保持一致。"""
    return GithubAuthClient(get_settings().storage_proxy)


def _row(db, user_id: str) -> GithubAuth:
    """取用户那一行，没有就建一行空的。"""
    pk = _user_pk(user_id)
    row = db.query(GithubAuth).filter(GithubAuth.user_id == pk).one_or_none()
    if row is None:
        row = GithubAuth(user_id=pk)
        db.add(row)
        db.flush()
    return row


def _mask(token: str) -> str | None:
    """脱敏摘要：够长的令牌只露首尾各 4 位。"""
    if not token:
        return None
    if len(token) <= 8:
        return f"{token[:2]}…"
    return f"{token[:4]}…{token[-4:]}"


def _status_of(row: GithubAuth, *, valid: bool | None) -> schemas.GithubAuthStatusView:
    return schemas.GithubAuthStatusView(
        configured=bool(row.access_token),
        valid=valid,
        source=row.source or None,
        login=row.login or None,
        maskedToken=_mask(row.access_token),
        expiresAt=row.expires_at or None,
        needsReauthorization=False,
        clientIdConfigured=bool(_client_id()),
    )


def _refresh_if_needed(row: GithubAuth) -> bool:
    """OAuth 令牌临近过期时刷新一次。返回是否需要重新授权（刷新失败且令牌已死）。"""
    if row.source != "oauth" or not row.access_token:
        return False
    if not row.expires_at or row.expires_at > int(time.time()) + _REFRESH_WINDOW:
        return False
    if not row.refresh_token:
        return True
    try:
        exchange = _client().refresh_access_token(_client_id(), row.refresh_token)
    except GithubTransportError:
        return True
    if not exchange.access_token:
        return True
    _apply_exchange(row, exchange)
    return False


def _apply_exchange(row: GithubAuth, exchange: TokenExchange) -> None:
    row.access_token = exchange.access_token or row.access_token
    if exchange.refresh_token:
        row.refresh_token = exchange.refresh_token
    if exchange.scope:
        row.scope = exchange.scope
    if exchange.expires_in is not None:
        row.expires_at = int(time.time()) + max(exchange.expires_in, 0)
    if exchange.refresh_token_expires_in is not None:
        row.refresh_expires_at = int(time.time()) + max(exchange.refresh_token_expires_in, 0)


def status(user_id: str) -> schemas.GithubAuthStatusView:
    """脱敏状态。仅在这里校验令牌有效性，校验失败不清库。"""
    with SessionLocal() as db:
        row = _row(db, user_id)
        if not row.access_token:
            view = _status_of(row, valid=None)
            db.commit()
            return view
        needs_reauth = _refresh_if_needed(row)
        token = row.access_token
        login = row.login
        db.commit()

    valid: bool | None = None
    try:
        user = _client().get_user(token)
        valid = True
        login = user.login or login
        with SessionLocal() as db:
            target = _row(db, user_id)
            target.login = login
            db.commit()
    except GithubTransportError as exc:
        # 401 判定失效；网络不可达保持 None，不让设置页误清令牌
        valid = False if exc.unauthorized else None
        needs_reauth = needs_reauth or exc.unauthorized

    with SessionLocal() as db:
        row = _row(db, user_id)
        view = _status_of(row, valid=valid)
        db.commit()
    return view.model_copy(update={"login": login or None, "needsReauthorization": needs_reauth})


def start_device_auth(user_id: str) -> schemas.GithubDeviceAuthStartView:
    """申请设备码。未配置 client_id 时直接拒绝，前端据此隐藏入口。"""
    client_id = _client_id()
    if not client_id:
        raise ApiError(
            400,
            ErrorCode.GITHUB_NOT_CONFIGURED,
            "尚未配置 GitHub OAuth App 的 client_id，暂不能使用设备码授权",
        )
    try:
        device = _client().request_device_code(client_id)
    except GithubTransportError as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc)) from exc
    if not device.device_code or not device.user_code or not device.verification_uri:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "GitHub 未返回完整的设备授权信息")

    now = time.time()
    session_id = uuid.uuid4().hex
    with _sessions_lock:
        for key, item in list(_sessions.items()):
            if item.expires_at <= now:
                del _sessions[key]
        _sessions[session_id] = _PendingSession(
            device_code=device.device_code,
            expires_at=now + device.expires_in,
            interval_seconds=device.interval_seconds,
        )
    return schemas.GithubDeviceAuthStartView(
        sessionId=session_id,
        verificationUri=device.verification_uri,
        userCode=device.user_code,
        expiresIn=device.expires_in,
        intervalSeconds=device.interval_seconds,
    )


def poll_device_auth(user_id: str, session_id: str) -> schemas.GithubDeviceAuthPollView:
    """按 GitHub 要求的频率轮询一次。早于 next_poll_at 的请求不触达 GitHub。"""
    with _sessions_lock:
        session = _sessions.get(session_id)
    if session is None:
        return schemas.GithubDeviceAuthPollView(
            state="expired", message="授权会话已失效，请重新开始授权。"
        )

    now = time.time()
    if session.expires_at <= now:
        _drop_session(session_id)
        return schemas.GithubDeviceAuthPollView(
            state="expired", message="GitHub 设备码已过期，请重新开始授权。"
        )
    with session.lock:
        if session.next_poll_at > now:
            return schemas.GithubDeviceAuthPollView(
                state="pending",
                message="等待在 GitHub 页面完成授权。",
                retryAfter=max(1, int(session.next_poll_at - now)),
            )
        session.next_poll_at = now + session.interval_seconds
        device_code = session.device_code
        interval = session.interval_seconds

    client_id = _client_id()
    if not client_id:
        _drop_session(session_id)
        raise ApiError(
            400,
            ErrorCode.GITHUB_NOT_CONFIGURED,
            "尚未配置 GitHub OAuth App 的 client_id，暂不能使用设备码授权",
        )
    try:
        exchange = _client().exchange_device_code(client_id, device_code)
    except GithubTransportError as exc:
        # 网络抖动不终止会话，下一轮再试
        return schemas.GithubDeviceAuthPollView(
            state="pending", message=str(exc), retryAfter=interval
        )

    if exchange.access_token:
        try:
            user = _client().get_user(exchange.access_token)
        except GithubTransportError as exc:
            raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc)) from exc
        with SessionLocal() as db:
            row = _row(db, user_id)
            row.source = "oauth"
            row.refresh_token = ""
            row.expires_at = 0
            row.refresh_expires_at = 0
            _apply_exchange(row, exchange)
            row.login = user.login
            db.commit()
        _drop_session(session_id)
        return schemas.GithubDeviceAuthPollView(
            state="authorized", message="GitHub 授权成功。", status=status(user_id)
        )

    error_code = (exchange.error or "").strip().lower()
    if error_code == _POLL_PENDING:
        return schemas.GithubDeviceAuthPollView(
            state="pending", message="等待在 GitHub 页面完成授权。", retryAfter=interval
        )
    if error_code == _POLL_SLOW_DOWN:
        # GitHub 要求降频：间隔至少 +5 秒，且不低于 10 秒
        with session.lock:
            session.interval_seconds = max(session.interval_seconds + 5, 10)
            session.next_poll_at = time.time() + session.interval_seconds
            slower = session.interval_seconds
        return schemas.GithubDeviceAuthPollView(
            state="slow_down", message="GitHub 要求降低轮询频率，稍后继续。", retryAfter=slower
        )
    if error_code == _POLL_DENIED:
        _drop_session(session_id)
        return schemas.GithubDeviceAuthPollView(state="denied", message="GitHub 授权已被拒绝。")
    if error_code in _POLL_EXPIRED:
        _drop_session(session_id)
        return schemas.GithubDeviceAuthPollView(
            state="expired", message="GitHub 设备码已过期，请重新开始授权。"
        )
    _drop_session(session_id)
    return schemas.GithubDeviceAuthPollView(state="failed", message="GitHub 授权失败，请重新开始。")


def set_manual_token(user_id: str, token: str) -> schemas.GithubAuthStatusView:
    """手动 PAT 兜底：覆盖现有凭据并清掉 OAuth 元数据，避免拿旧 refresh_token 去刷新。"""
    normalized = token.strip()
    if not normalized:
        raise ApiError(400, ErrorCode.BAD_REQUEST, "GitHub 令牌不能为空")
    login = ""
    try:
        login = _client().get_user(normalized).login
    except GithubTransportError as exc:
        # 只有 401 才算填错；网络不通也允许先存下，等状态刷新时再判定
        if exc.unauthorized:
            raise ApiError(400, ErrorCode.BAD_REQUEST, "GitHub 令牌无效或已失效") from exc
    with SessionLocal() as db:
        row = _row(db, user_id)
        row.source = "manual"
        row.access_token = normalized
        row.refresh_token = ""
        row.expires_at = 0
        row.refresh_expires_at = 0
        row.scope = ""
        row.login = login
        db.commit()
    return status(user_id)


def clear_token(user_id: str) -> None:
    """解除授权：凭据整行清空，但保留行本身。"""
    with SessionLocal() as db:
        row = _row(db, user_id)
        row.source = ""
        row.access_token = ""
        row.refresh_token = ""
        row.scope = ""
        row.login = ""
        row.expires_at = 0
        row.refresh_expires_at = 0
        db.commit()


def access_token(user_id: str) -> str:
    """给服务端出站用例取可用的访问令牌。禁止投影到任何接口响应。"""
    with SessionLocal() as db:
        row = _row(db, user_id)
        if row.access_token:
            _refresh_if_needed(row)
        token = row.access_token
        db.commit()
    return token


def _drop_session(session_id: str) -> None:
    with _sessions_lock:
        _sessions.pop(session_id, None)
