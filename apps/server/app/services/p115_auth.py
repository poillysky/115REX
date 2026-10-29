"""115 扫码授权（docs/07 §2.2）。设备码 + PKCE 的状态机，形态照 GitHub 设备码流程。

三段式：申请设备码 → 前端把二维码内容渲染成图给用户扫 → 前端按服务端给定的间隔轮询。
令牌落 `storage_bindings` 表；对外只给绑定状态，令牌原文绝不出现在任何响应里。
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.api import schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.integrations.p115 import P115Client, P115TransportError, TokenPair
from app.storage.db import SessionLocal
from app.storage.models import StorageBinding, utcnow

_PROVIDER = "115"

# 扫码设备码的存活时间与轮询间隔。115 未告知有效期，按 5 分钟给。
_SESSION_TTL_SECONDS = 300
_POLL_INTERVAL_SECONDS = 2

# 访问令牌剩余时间不足这么多秒：先尝试刷新，刷不动就报「即将失效」
_REFRESH_WINDOW = 300

# 115 没回 expires_in 时按访问令牌 2 小时有效推算
_ASSUMED_ACCESS_TTL_SECONDS = 7200

# 115 限频后的冷却时间，期间不再尝试刷新
_REFRESH_COOLDOWN_SECONDS = 300

# 只有这几个业务码说明刷新令牌本身不被 115 承认（格式错误 40140114 等参数类不算）
_CODES_REVOKED = (40140001, 40140101, 40140103, 40140104, 40140107, 40140119)

# 账号概况（昵称 / 容量）的缓存时长：容量变化慢，读太勤会触发 115 频率限制
_INFO_TTL_SECONDS = 300

# 绑定状态：正常 / 待续期 / 已失效 / 未绑定。
# 「已失效」只认刷新令牌被 115 判作废（见 _CODES_REVOKED）；限频、网络抖动、请求
# 参数出错都不算，此时看访问令牌的剩余时间：还能用就是正常，用完了报「待续期」，
# 服务端下一轮照样会再刷一次，刷成功就自动回到正常。


@dataclass
class _PendingSession:
    """进程内扫码会话。校验码只在这里，重启即失效，用户重新扫一次即可。"""

    uid: str
    time: int
    sign: str
    code_verifier: str
    expires_at: float
    interval_seconds: int
    next_poll_at: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)


_sessions: dict[str, _PendingSession] = {}
_sessions_lock = threading.Lock()


def _app_id() -> str:
    return get_settings().u115_app_id.strip()


def _client() -> P115Client:
    """出口代理与 115 出站保持一致，取设置页里的网络配置。"""
    return P115Client(get_settings().storage_proxy)


def _user_pk(user_id: str) -> int:
    try:
        return int(user_id.removeprefix("u-"))
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc


def _row(db, user_id: str) -> StorageBinding:
    """取该用户 115 那一行，没有就建一行空白的。"""
    pk = _user_pk(user_id)
    row = (
        db.query(StorageBinding)
        .filter(StorageBinding.user_id == pk, StorageBinding.provider == _PROVIDER)
        .one_or_none()
    )
    if row is None:
        row = StorageBinding(user_id=pk, provider=_PROVIDER, status="unbound")
        db.add(row)
        db.flush()
    return row


def _access_expires_at(row: StorageBinding) -> int:
    """访问令牌的推定到期时间。115 偶尔不回 expires_in，按 2 小时算。"""
    return row.refresh_at + (row.expires_in or _ASSUMED_ACCESS_TTL_SECONDS)


def _status_of(row: StorageBinding) -> schemas.BindingStatus:
    """折算绑定状态。

    令牌被清空是 unbound；访问令牌还能用就是 healthy。访问令牌到期而刷新没接上
    是 expiring——此时 115 已经用不了了，但刷新令牌并没有被判定作废，不能催用户
    重新扫码（115 限频时重扫一遍也是白扫）。只有刷新令牌被 115 判作废才是 expired，
    而且之后只要刷新成功，绑定会自动恢复成 healthy。
    """
    if not row.access_token or not row.refresh_token:
        return "unbound"
    if row.status == "expired":
        return "expired"
    if _access_expires_at(row) <= int(time.time()) + _REFRESH_WINDOW:
        return "expiring"
    return "healthy"


def _epoch(value: datetime | None) -> int:
    """SQLite 读回的 datetime 不带时区，按 UTC 解释再取时间戳。"""
    if value is None:
        return int(time.time())
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def _view(row: StorageBinding) -> schemas.StorageBindingView:
    # 授权没有固定到期日：访问令牌 2 小时一刷，只要刷新令牌还能用就一直有效，
    # 所以不再下发 expiresAt（07 §2.2 只约定状态，不下发令牌时间）
    quota = (
        schemas.StorageQuotaView(totalBytes=row.total_bytes, usedBytes=row.used_bytes)
        if row.total_bytes
        else None
    )
    return schemas.StorageBindingView(
        provider=row.provider,
        status=_status_of(row),
        displayName=row.account_name or ("115 账号" if row.access_token else None),
        avatarUrl=row.account_avatar or None,
        vipLevel=row.vip_level or None,
        vipExpire=row.vip_expire or None,
        updatedAt=_epoch(row.updated_at),
        syncedAt=row.info_at or None,
        quota=quota,
    )


def _is_revoked(exc: P115TransportError) -> bool:
    """115 是否明确表示「刷新令牌不认了」。

    只认已知的作废码：格式错误、参数不对（40140114 之类）同样是明确拒绝，但那说明
    服务端把请求写坏了，不能拿用户的授权去背锅；未知的新码也一律先当成没结论。
    """
    return exc.code is not None and exc.code in _CODES_REVOKED


def _refresh_if_needed(row: StorageBinding) -> None:
    """访问令牌临近过期时刷新一次。

    刷新失败分三种：网络抖动原样保留，下次再来；115 限频（刷新过于频繁）也保留，
    等冷却时间过了再试；刷新令牌被 115 判作废才置 expired。
    """
    if not row.refresh_token:
        return
    if row.access_token and row.status != "expired":
        lifetime = row.expires_in or _ASSUMED_ACCESS_TTL_SECONDS
        if row.refresh_at + lifetime > int(time.time()) + _REFRESH_WINDOW:
            return
    # 刚被限频过就先别打 115，等冷却结束
    if row.throttle_until > int(time.time()):
        return
    try:
        tokens = _client().refresh_access_token(row.refresh_token)
    except P115TransportError as exc:
        if exc.throttled:
            # 限频只是要求放慢，不代表授权失效
            row.throttle_until = int(time.time()) + _REFRESH_COOLDOWN_SECONDS
            return
        if _is_revoked(exc):
            row.status = "expired"
            row.updated_at = utcnow()
        return
    row.throttle_until = 0
    if tokens.access_token:
        _apply_tokens(row, tokens)
        row.status = "healthy"


def _sync_info(row: StorageBinding, *, force: bool = False) -> None:
    """拉一次账号概况（昵称 / 头像 / 会员 / 容量）并写回。

    读失败不影响绑定状态：网络抖动保留上次的值，等下次访问再试。
    """
    # 即将失效也要照常取容量：此时 115 多半还认这个访问令牌，卡片不该空着
    if not row.access_token or row.status == "expired":
        return
    if not force and row.info_at + _INFO_TTL_SECONDS > int(time.time()):
        return
    try:
        info = _client().user_info(row.access_token)
    except P115TransportError as exc:
        if exc.throttled or exc.retryable:
            return
        # 只有 401 才说明令牌不认了：先刷一次再用新令牌取，刷不动才认定授权作废。
        # 其他业务错误（接口改版、字段变动）重取一次也没用，保留绑定状态等下次再试。
        if not exc.unauthorized:
            return
        row.expires_in = 0
        _refresh_if_needed(row)
        if row.status == "expired":
            return
        try:
            info = _client().user_info(row.access_token)
        except P115TransportError:
            return
    if info.name:
        row.account_name = info.name[:128]
    if info.avatar_url:
        row.account_avatar = info.avatar_url[:512]
    row.vip_level = (info.vip_level or "")[:64]
    row.vip_expire = info.vip_expire
    row.total_bytes = info.total_bytes
    row.used_bytes = info.used_bytes
    row.info_at = int(time.time())


def bindings(user_id: str) -> schemas.StorageBindingsResponse:
    """网盘绑定列表。未绑定也给一条，前端据此展示「去绑定」。"""
    with SessionLocal() as db:
        row = _row(db, user_id)
        _refresh_if_needed(row)
        _sync_info(row)
        db.commit()
        return schemas.StorageBindingsResponse(bindings=[_view(row)])


def _ensure_token(user_id: str) -> str:
    """取一个可用的访问令牌，授权作废时给空串。

    限频或网络抖动不改变绑定状态，拿到的还是原来那个访问令牌（可能已过期），
    调用方按 115 的拒绝自行重试即可。
    """
    with SessionLocal() as db:
        row = _row(db, user_id)
        _refresh_if_needed(row)
        # expired 时令牌已被认定作废，不能再拿去调 115
        token = "" if row.status == "expired" else row.access_token
        db.commit()
    return token


def _apply_tokens(row: StorageBinding, tokens: TokenPair) -> None:
    row.access_token = tokens.access_token or row.access_token
    if tokens.refresh_token:
        row.refresh_token = tokens.refresh_token
    row.refresh_at = int(time.time())
    if tokens.expires_in is not None:
        row.expires_in = max(tokens.expires_in, 0)
    row.status = _status_of(row)
    row.updated_at = utcnow()


def start(user_id: str) -> schemas.P115AuthStartView:
    """申请扫码设备码。只下发二维码内容，PKCE 校验码留在服务端。"""
    app_id = _app_id()
    if not app_id:
        raise ApiError(
            400, ErrorCode.STORAGE_AUTH_REQUIRED, "尚未配置 115 应用 ID，暂不能扫码绑定"
        )
    try:
        device = _client().request_device_code(app_id)
    except P115TransportError as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc)) from exc

    now = time.time()
    session_id = uuid.uuid4().hex
    with _sessions_lock:
        for key, item in list(_sessions.items()):
            if item.expires_at <= now:
                del _sessions[key]
        _sessions[session_id] = _PendingSession(
            uid=device.uid,
            time=device.time,
            sign=device.sign,
            code_verifier=device.code_verifier,
            expires_at=now + _SESSION_TTL_SECONDS,
            interval_seconds=_POLL_INTERVAL_SECONDS,
        )
    return schemas.P115AuthStartView(
        sessionId=session_id,
        qrcode=device.qrcode,
        expiresIn=_SESSION_TTL_SECONDS,
        intervalSeconds=_POLL_INTERVAL_SECONDS,
    )


def poll(user_id: str, session_id: str) -> schemas.P115AuthPollView:
    """轮询一次扫码结果。早于 next_poll_at 的请求不触达 115。"""
    with _sessions_lock:
        session = _sessions.get(session_id)
    if session is None:
        return schemas.P115AuthPollView(
            state="expired", message="扫码会话已失效，请重新生成二维码。"
        )

    now = time.time()
    if session.expires_at <= now:
        _drop(session_id)
        return schemas.P115AuthPollView(
            state="expired", message="二维码已过期，请重新生成。"
        )
    with session.lock:
        if session.next_poll_at > now:
            return schemas.P115AuthPollView(
                state="pending",
                message="等待在 115 手机端扫码确认。",
                retryAfter=max(1, int(session.next_poll_at - now)),
            )
        session.next_poll_at = now + session.interval_seconds
        uid, time_value, sign = session.uid, session.time, session.sign
        verifier = session.code_verifier
        interval = session.interval_seconds

    try:
        status = _client().poll_qrcode(uid, time_value, sign)
    except P115TransportError as exc:
        # 网络抖动不终止会话，下一轮再试
        return schemas.P115AuthPollView(state="pending", message=str(exc), retryAfter=interval)

    if status.expired:
        _drop(session_id)
        return schemas.P115AuthPollView(
            state="expired", message=status.message or "二维码已过期，请重新生成。"
        )
    if not status.confirmed:
        message = (
            "已扫码，请在手机端点击确认。"
            if status.scanned
            else status.message or "等待在 115 手机端扫码确认。"
        )
        return schemas.P115AuthPollView(state="pending", message=message, retryAfter=interval)

    try:
        tokens = _client().exchange_device_code(uid, verifier)
    except P115TransportError as exc:
        _drop(session_id)
        return schemas.P115AuthPollView(state="failed", message=str(exc))
    if tokens.pending or not tokens.access_token:
        return schemas.P115AuthPollView(
            state="pending", message="已扫码，正在等待 115 返回令牌。", retryAfter=interval
        )

    with SessionLocal() as db:
        row = _row(db, user_id)
        _apply_tokens(row, tokens)
        # 刚绑上就顺手取一次昵称与容量，卡片不必等下一轮刷新才有信息
        _sync_info(row, force=True)
        db.commit()
        view = _view(row)
    _drop(session_id)
    return schemas.P115AuthPollView(state="authorized", message="115 绑定成功。", binding=view)


def unbind(user_id: str) -> schemas.StorageBindingsResponse:
    """解绑：令牌与账号概况一并清空，但保留行本身。"""
    with SessionLocal() as db:
        row = _row(db, user_id)
        row.access_token = ""
        row.refresh_token = ""
        row.refresh_at = 0
        row.expires_in = 0
        row.account_name = ""
        row.account_avatar = ""
        row.vip_level = ""
        row.vip_expire = 0
        row.total_bytes = 0
        row.used_bytes = 0
        row.info_at = 0
        row.throttle_until = 0
        row.status = "unbound"
        row.updated_at = utcnow()
        db.commit()
        return schemas.StorageBindingsResponse(bindings=[_view(row)])


def access_token(user_id: str) -> str:
    """给服务端出站用例取可用的访问令牌。禁止投影到任何接口响应。"""
    return _ensure_token(user_id)


def _drop(session_id: str) -> None:
    with _sessions_lock:
        _sessions.pop(session_id, None)
