"""播放信息服务（docs/07 §2.6、docs/06 §4）。

内部顺序：探测 → 解析直链 → 返回。客户端只拿到地址、请求头、有效期。
115 直链解析尚未实现（docs/06 §11 Q1），未接时返回「适配器未就绪」，客户端当作可重试错误。
"""

from __future__ import annotations

import time

from app.api import schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.services import demo_data

PLAY_URL_TTL_SECONDS = 900  # 短链有效期，待实测（docs/07 §5 Q3）
REFRESH_LIMIT_PER_HOUR = 10

# item_id -> 最近一小时的签发次数
_issue_log: dict[str, list[int]] = {}


def _throttle(item_id: str) -> None:
    now = int(time.time())
    stamps = [t for t in _issue_log.get(item_id, []) if now - t < 3600]
    if len(stamps) >= REFRESH_LIMIT_PER_HOUR:
        raise ApiError(
            429, ErrorCode.PLAY_INFO_RATE_LIMITED, "刷新太频繁，请稍后再试", 30
        )
    stamps.append(now)
    _issue_log[item_id] = stamps


def issue(item_id: str, device_id: str | None) -> schemas.PlayInfoResponse:
    settings = get_settings()
    item = demo_data.find_item(item_id)
    if item is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "条目已删除，请刷新列表")

    if not settings.mock_mode:
        # 真实适配器未实现前统一走这里
        raise ApiError(
            503, ErrorCode.PLAY_ADAPTER_NOT_READY, "播放适配器未就绪，请稍后重试", 10
        )

    _throttle(item_id)
    now = int(time.time())
    return schemas.PlayInfoResponse(
        # 演示地址；真实实现由 integrations/115 解析后返回，响应里不放任何凭据
        url=f"https://cdn.example.invalid/115/{item.id}?expires={now + PLAY_URL_TTL_SECONDS}",
        headers={},
        expiresAt=now + PLAY_URL_TTL_SECONDS,
        playToken=f"dev-play-token-{item.id}-{device_id or 'anon'}",
        startPositionSeconds=item.progressSeconds,
        subtitles=item.subtitles,
        maxRefresh=REFRESH_LIMIT_PER_HOUR,
    )
