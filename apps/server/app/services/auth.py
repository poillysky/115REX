"""鉴权服务（docs/06 §7、docs/07 §2.1）。

令牌模型：JWT access（2h）+ 不透明 refresh（30d 滚动），服务端只存 refresh 的 SHA256。
重放检测：旧 refresh 被复用 → 吊销该设备全部令牌。
账号存 SQLite（首个注册的账号即所有者）；refresh 记录仍在内存，重启后需重新登录。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import func, select

from app.api import schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.storage.db import SessionLocal
from app.storage.models import User

# 用户名规则：字母数字与 . _ -，3–32 位；密码至少 6 位
USERNAME_MIN = 3
USERNAME_MAX = 32
PASSWORD_MIN = 6


@dataclass
class _RefreshRecord:
    device_id: str
    user_id: str
    expires_at: int
    rotated: bool = False


_refresh_store: dict[str, _RefreshRecord] = {}


# ---------------------------------------------------------------- JWT（HS256，无额外依赖）


def _b64(raw: bytes) -> str:
    return urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(message: bytes, secret: str) -> str:
    return _b64(hmac.new(secret.encode(), message, hashlib.sha256).digest())


def _issue_access(user_id: str, device_id: str) -> tuple[str, int]:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "dev": device_id,
        "iat": now,
        "exp": now + settings.access_ttl_seconds,
    }
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    header = _b64(b'{"alg":"HS256","typ":"JWT"}')
    return f"{header}.{body}.{_sign(f'{header}.{body}'.encode(), settings.secret_key)}", payload["exp"]


def decode_access(token: str) -> dict:
    settings = get_settings()
    try:
        header, body, signature = token.split(".")
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc
    expected = _sign(f"{header}.{body}".encode(), settings.secret_key)
    if not hmac.compare_digest(signature, expected):
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录")
    payload = json.loads(_unb64(body))
    if payload.get("exp", 0) < int(time.time()):
        raise ApiError(401, ErrorCode.TOKEN_EXPIRED, "登录已过期")
    return payload


# ---------------------------------------------------------------- 用户


def _user_view(user: User) -> schemas.UserView:
    # v 取头像文件的修改时间，换头像后地址变化，浏览器才会重新拉图
    version = ""
    if user.avatar:
        path = _avatar_path(user.avatar)
        version = str(int(path.stat().st_mtime)) if path.exists() else ""
    return schemas.UserView(
        id=f"u-{user.id}",
        username=user.username,
        displayName=user.display_name or user.username,
        avatarUrl=f"/api/v1/auth/avatar?u=u-{user.id}&v={version}" if user.avatar else None,
    )


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds))
    return hmac.compare_digest(digest.hex(), expected)


def _user_pk(user_id: str) -> int:
    """令牌里是 `u-<pk>`，这里还原成主键。"""
    try:
        return int(user_id.removeprefix("u-"))
    except ValueError as exc:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录") from exc


def _validate_credentials(username: str, password: str) -> str:
    name = username.strip()
    if not (USERNAME_MIN <= len(name) <= USERNAME_MAX):
        raise ApiError(400, ErrorCode.BAD_REQUEST, f"用户名需 {USERNAME_MIN}–{USERNAME_MAX} 个字符")
    if not all(ch.isalnum() or ch in "._-" for ch in name):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "用户名只能用字母、数字与 . _ -")
    if len(password) < PASSWORD_MIN:
        raise ApiError(400, ErrorCode.BAD_REQUEST, f"密码至少 {PASSWORD_MIN} 位")
    return name


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _issue_refresh(user_id: str, device_id: str) -> str:
    settings = get_settings()
    token = secrets.token_urlsafe(48)
    _refresh_store[_hash(token)] = _RefreshRecord(
        device_id=device_id,
        user_id=user_id,
        expires_at=int(time.time()) + settings.refresh_ttl_seconds,
    )
    return token


def _revoke_device(device_id: str) -> None:
    for record in _refresh_store.values():
        if record.device_id == device_id:
            record.rotated = True


def _token_pair(user_id: str, device_id: str) -> dict:
    settings = get_settings()
    access, _ = _issue_access(user_id, device_id)
    return {
        "accessToken": access,
        "refreshToken": _issue_refresh(user_id, device_id),
        "expiresIn": settings.access_ttl_seconds,
    }


# ---------------------------------------------------------------- 对外


def login(payload: schemas.LoginRequest, device_id: str | None) -> schemas.LoginResponse:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == payload.username.strip()))
    if user is None or not _verify_password(payload.password, user.password_hash):
        raise ApiError(401, ErrorCode.INVALID_CREDENTIALS, "账号或密码不正确")
    user_id = f"u-{user.id}"
    device = device_id or "dev-unknown"
    return schemas.LoginResponse(
        user=_user_view(user), **_token_pair(user_id, device)
    )


def registration_open() -> bool:
    """一个账号都没有时开放注册；创建首个账号后关闭（单用户自托管）。"""
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(User)) == 0


def register(payload: schemas.RegisterRequest, device_id: str | None) -> schemas.LoginResponse:
    username = _validate_credentials(payload.username, payload.password)
    if not registration_open():
        raise ApiError(403, ErrorCode.REGISTRATION_CLOSED, "账号已创建，请直接登录")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)) is not None:
            raise ApiError(409, ErrorCode.USERNAME_TAKEN, "该用户名已被占用")
        user = User(username=username, password_hash=_hash_password(payload.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        view = _user_view(user)
        user_id = view.id
    device = device_id or "dev-unknown"
    return schemas.LoginResponse(user=view, **_token_pair(user_id, device))


def refresh(payload: schemas.RefreshRequest, device_id: str | None) -> schemas.RefreshResponse:
    key = _hash(payload.refreshToken)
    record = _refresh_store.get(key)
    if record is None:
        raise ApiError(401, ErrorCode.REFRESH_EXPIRED, "登录已失效，请重新登录")
    if record.expires_at < int(time.time()):
        raise ApiError(401, ErrorCode.REFRESH_EXPIRED, "登录已失效，请重新登录")
    if record.rotated:
        # 旧 refresh 被复用 → 吊销该设备全部令牌
        _revoke_device(record.device_id)
        raise ApiError(401, ErrorCode.REFRESH_EXPIRED, "登录状态异常，请重新登录")

    record.rotated = True
    return schemas.RefreshResponse(**_token_pair(record.user_id, record.device_id or device_id or ""))


def logout(device_id: str | None) -> None:
    if device_id:
        _revoke_device(device_id)


def me(user_id: str) -> schemas.MeResponse:
    settings = get_settings()
    with SessionLocal() as db:
        user = db.get(User, _user_pk(user_id))
    if user is None:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录")
    return schemas.MeResponse(
        user=_user_view(user),
        server=schemas.ServerInfo(version="0.1.0", mockMode=settings.mock_mode),
        capabilities=schemas.CapabilityView(
            play=settings.mock_mode,
            playbackAdapterReady=settings.mock_mode,
        ),
    )


# ---------------------------------------------------------------- 账号资料


AVATAR_DIR = Path(__file__).resolve().parents[2] / "data" / "avatars"
AVATAR_MAX_BYTES = 2 * 1024 * 1024
AVATAR_FETCH_TIMEOUT = 10.0
DISPLAY_NAME_MAX = 32
PASSWORD_MAX = 128


def _avatar_path(filename: str) -> Path:
    return AVATAR_DIR / filename


def _save_avatar(user: User, data_url: str) -> str:
    """把头像落盘，返回文件名。接受 data URL 或图标库里的 http(s) 图片地址。"""
    raw = (
        _decode_avatar_data_url(data_url)
        if data_url.startswith("data:")
        else _download_avatar(data_url)
    )

    filename = f"avatar-u{user.id}.png"
    target = _avatar_path(filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    return filename


def _decode_avatar_data_url(data_url: str) -> bytes:
    header, _, payload = data_url.partition(",")
    if "base64" not in header or not header.startswith("data:image/"):
        raise ApiError(400, ErrorCode.AVATAR_INVALID, "头像格式不支持")
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ApiError(400, ErrorCode.AVATAR_INVALID, "头像内容无法解析") from exc
    if len(raw) > AVATAR_MAX_BYTES:
        raise ApiError(400, ErrorCode.AVATAR_INVALID, "头像不能超过 2 MB")
    return raw


def _download_avatar(url: str) -> bytes:
    """从图标库地址下载头像。只收图片类型，超限即断，避免被当成任意下载器。"""
    if not url.startswith(("https://", "http://")):
        raise ApiError(400, ErrorCode.AVATAR_INVALID, "头像地址必须以 http(s) 开头")
    try:
        with httpx.Client(
            timeout=AVATAR_FETCH_TIMEOUT,
            follow_redirects=True,
            trust_env=False,
            proxy=get_settings().storage_proxy.strip() or None,
        ) as client:
            with client.stream("GET", url, headers={"User-Agent": "115REX"}) as response:
                response.raise_for_status()
                if not response.headers.get("content-type", "").startswith("image/"):
                    raise ApiError(400, ErrorCode.AVATAR_INVALID, "该地址不是图片")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > AVATAR_MAX_BYTES:
                        raise ApiError(400, ErrorCode.AVATAR_INVALID, "头像不能超过 2 MB")
                    chunks.append(chunk)
    except httpx.HTTPError as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "头像图片下载失败，请换一个图标") from exc
    return b"".join(chunks)


def read_avatar(user_id: str) -> bytes:
    with SessionLocal() as db:
        user = db.get(User, _user_pk(user_id))
    if user is None or not user.avatar:
        raise ApiError(404, ErrorCode.NOT_FOUND, "头像不存在")
    path = _avatar_path(user.avatar)
    if not path.exists():
        raise ApiError(404, ErrorCode.NOT_FOUND, "头像不存在")
    return path.read_bytes()


def update_profile(user_id: str, payload: schemas.ProfileUpdateRequest) -> schemas.UserView:
    with SessionLocal() as db:
        user = db.get(User, _user_pk(user_id))
        if user is None:
            raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录")
        if payload.displayName is not None:
            name = payload.displayName.strip()
            if not name:
                user.display_name = None
            else:
                if len(name) > DISPLAY_NAME_MAX:
                    raise ApiError(400, ErrorCode.BAD_REQUEST, f"昵称最多 {DISPLAY_NAME_MAX} 个字符")
                user.display_name = name
        if payload.avatarUrl:
            user.avatar = _save_avatar(user, payload.avatarUrl)
        db.commit()
        db.refresh(user)
        return _user_view(user)


def change_password(user_id: str, payload: schemas.PasswordUpdateRequest) -> None:
    new = payload.newPassword
    if len(new) < PASSWORD_MIN:
        raise ApiError(400, ErrorCode.BAD_REQUEST, f"密码至少 {PASSWORD_MIN} 位")
    if len(new) > PASSWORD_MAX:
        raise ApiError(400, ErrorCode.BAD_REQUEST, f"密码最多 {PASSWORD_MAX} 位")
    with SessionLocal() as db:
        user = db.get(User, _user_pk(user_id))
        if user is None:
            raise ApiError(401, ErrorCode.TOKEN_MISSING, "登录状态无效，请重新登录")
        if not _verify_password(payload.currentPassword, user.password_hash):
            raise ApiError(400, ErrorCode.INVALID_CREDENTIALS, "当前密码不正确")
        user.password_hash = _hash_password(new)
        db.commit()
    # 改密后强制所有设备重新登录
    for record in _refresh_store.values():
        if record.user_id == user_id:
            record.rotated = True
