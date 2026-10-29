"""影视库服务（docs/07 §2.5、§2.7）。

库内搜索只查已入库条目，与 /search 是两个接口，不要混用。
进度按客户端时间戳取较新者，避免多端互相覆盖。
"""

from __future__ import annotations

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.services import demo_data

# item_id -> (positionSeconds, clientTimestamp)，用于「取较新者」的判定
_progress_clock: dict[str, int] = {}


def list_items(
    cursor: str | None, limit: int, sort: str, query: str | None
) -> schemas.MediaItemListResponse:
    items = demo_data.items()

    if query:
        keyword = query.strip().lower()
        items = [i for i in items if keyword in i.title.lower() or keyword in (i.originalTitle or "").lower()]

    if sort == "title":
        items = sorted(items, key=lambda i: i.title)
    else:  # recent：最近播放优先，未播放排后
        items = sorted(items, key=lambda i: i.lastPlayedAt or 0, reverse=True)

    start = int(cursor) if cursor and cursor.isdigit() else 0
    page = items[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(items) else None
    return schemas.MediaItemListResponse(
        items=[schemas.MediaItemView(**item.model_dump()) for item in page],
        nextCursor=next_cursor,
    )


def get_item(item_id: str) -> schemas.MediaItemDetail:
    item = demo_data.find_item(item_id)
    if item is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "条目已删除，请刷新列表")
    return item


def list_dirs(path: str | None) -> schemas.DirsResponse:
    return demo_data.dirs(path)


def continue_watching() -> schemas.ContinueResponse:
    played = [item for item in demo_data.items() if item.progressSeconds > 0 and item.lastPlayedAt]
    played.sort(key=lambda i: i.lastPlayedAt or 0, reverse=True)
    return schemas.ContinueResponse(
        items=[schemas.MediaItemView(**item.model_dump()) for item in played]
    )


def put_progress(item_id: str, payload: schemas.ProgressRequest) -> schemas.ProgressResponse:
    item = get_item(item_id)
    last_client_ts = _progress_clock.get(item_id, 0)
    if payload.clientTimestamp >= last_client_ts:
        _progress_clock[item_id] = payload.clientTimestamp
        item.progressSeconds = payload.positionSeconds
        item.lastPlayedAt = payload.clientTimestamp
    return schemas.ProgressResponse(
        progressSeconds=item.progressSeconds,
        lastPlayedAt=item.lastPlayedAt or 0,
    )


def put_favorite(item_id: str, payload: schemas.FavoriteRequest) -> schemas.FavoriteResponse:
    item = get_item(item_id)
    item.favorite = payload.favorite
    return schemas.FavoriteResponse(favorite=item.favorite)
