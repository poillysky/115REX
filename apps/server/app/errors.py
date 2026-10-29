"""统一错误信封（docs/07 §3）。

所有业务错误都抛 ApiError，由 app 层统一转成
`{"code": "...", "message": "...", "retryAfter": 30}` 形状。
资源源级失败不抛这里 —— 那是搜索结果里的源状态，不是 HTTP 错误。
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after


class ErrorCode:
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_TARGET_DIR = "INVALID_TARGET_DIR"
    ACTION_NOT_SUPPORTED = "ACTION_NOT_SUPPORTED"

    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    REGISTRATION_CLOSED = "REGISTRATION_CLOSED"
    AVATAR_INVALID = "AVATAR_INVALID"
    TOKEN_MISSING = "TOKEN_MISSING"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    REFRESH_EXPIRED = "REFRESH_EXPIRED"

    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"

    STORAGE_AUTH_REQUIRED = "STORAGE_AUTH_REQUIRED"
    QBITTORRENT_NOT_READY = "QBITTORRENT_NOT_READY"

    GITHUB_NOT_CONFIGURED = "GITHUB_NOT_CONFIGURED"

    PLAY_URL_EXPIRED = "PLAY_URL_EXPIRED"
    PLAY_INFO_RATE_LIMITED = "PLAY_INFO_RATE_LIMITED"
    PLAY_ADAPTER_NOT_READY = "PLAY_ADAPTER_NOT_READY"

    SEARCH_RATE_LIMITED = "SEARCH_RATE_LIMITED"

    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    PROVIDER_NOT_READY = "PROVIDER_NOT_READY"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"

    INTERNAL_ERROR = "INTERNAL_ERROR"


def error_response(err: ApiError) -> JSONResponse:
    body: dict[str, object] = {"code": err.code, "message": err.message}
    if err.retry_after is not None:
        body["retryAfter"] = err.retry_after
    headers = {}
    if err.retry_after is not None:
        headers["Retry-After"] = str(err.retry_after)
    return JSONResponse(status_code=err.status, content=body, headers=headers)


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc)


async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # 内部异常不外泄：500 只给通用文案，堆栈进日志（docs/06 §10）
    return error_response(ApiError(500, ErrorCode.INTERNAL_ERROR, "服务暂时不可用，请稍后重试"))
