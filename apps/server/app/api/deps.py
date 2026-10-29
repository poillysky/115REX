"""FastAPI 依赖：鉴权、设备标识、分页参数。

api 层只用这里的依赖拿身份，不直接碰令牌细节。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, Query

from app.errors import ApiError, ErrorCode
from app.services import auth


def device_id(
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> str | None:
    return x_device_id


def current_claim(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """校验 access token，返回完整声明（需要 user_id 时用这个）。"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "请先登录")
    return auth.decode_access(authorization.split(" ", 1)[1].strip())


def current_device(
    claim: Annotated[dict, Depends(current_claim)],
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
) -> str:
    """校验 access token，返回设备 ID。"""
    return str(claim.get("dev") or x_device_id or "dev-unknown")


def pagination(
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query()] = None,
) -> tuple[int, str | None]:
    return limit, cursor


CurrentClaim = Annotated[dict, Depends(current_claim)]
CurrentDevice = Annotated[str, Depends(current_device)]
OptionalDevice = Annotated[str | None, Depends(device_id)]
Pagination = Annotated[tuple[int, str | None], Depends(pagination)]
