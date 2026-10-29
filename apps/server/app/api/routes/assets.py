"""字幕原文（docs/07 §2.9）。

鉴权二选一：请求头，或查询参数带播放令牌（播放器无法带请求头时用后者）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Query
from fastapi.responses import PlainTextResponse

from app.errors import ApiError, ErrorCode
from app.services import auth

router = APIRouter(prefix="/assets", tags=["assets"])

_DEMO_SRT = """1
00:00:01,000 --> 00:00:04,000
演示字幕：真实字幕接入后替换。

2
00:00:05,000 --> 00:00:09,000
字幕内容不经后端改写，仅做鉴权与转发。
"""


@router.get("/sub/{subtitle_id}", response_class=PlainTextResponse)
def get_subtitle(
    subtitle_id: str,
    authorization: Annotated[str | None, Header()] = None,
    play_token: Annotated[str | None, Query(alias="playToken")] = None,
) -> PlainTextResponse:
    if not play_token:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise ApiError(401, ErrorCode.TOKEN_MISSING, "请先登录")
        auth.decode_access(authorization.split(" ", 1)[1].strip())
    _ = subtitle_id
    return PlainTextResponse(_DEMO_SRT, media_type="text/plain; charset=utf-8")
