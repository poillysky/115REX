"""影视库、播放信息、进度与收藏（docs/07 §2.5–2.7）。"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api import deps, schemas
from app.services import library, play

router = APIRouter(prefix="/library", tags=["library"])


@router.get("/items", response_model=schemas.MediaItemListResponse)
def list_items(
    _: deps.CurrentDevice,
    page: deps.Pagination,
    sort: Annotated[Literal["recent", "title"], Query()] = "recent",
    q: Annotated[str | None, Query(description="库内搜索，只查已入库条目")] = None,
) -> schemas.MediaItemListResponse:
    limit, cursor = page
    return library.list_items(cursor, limit, sort, q)


@router.get("/items/{item_id}", response_model=schemas.MediaItemDetail)
def get_item(item_id: str, _: deps.CurrentDevice) -> schemas.MediaItemDetail:
    return library.get_item(item_id)


@router.get("/dirs", response_model=schemas.DirsResponse)
def list_dirs(
    _: deps.CurrentDevice,
    path: Annotated[str | None, Query(description="展开的目录；空为根")] = None,
) -> schemas.DirsResponse:
    return library.list_dirs(path)


@router.get("/continue", response_model=schemas.ContinueResponse)
def continue_watching(_: deps.CurrentDevice) -> schemas.ContinueResponse:
    return library.continue_watching()


@router.post("/items/{item_id}/play-info", response_model=schemas.PlayInfoResponse)
def play_info(item_id: str, device: deps.CurrentDevice) -> schemas.PlayInfoResponse:
    return play.issue(item_id, device)


@router.put("/items/{item_id}/progress", response_model=schemas.ProgressResponse)
def put_progress(
    item_id: str, payload: schemas.ProgressRequest, _: deps.CurrentDevice
) -> schemas.ProgressResponse:
    return library.put_progress(item_id, payload)


@router.put("/items/{item_id}/favorite", response_model=schemas.FavoriteResponse)
def put_favorite(
    item_id: str, payload: schemas.FavoriteRequest, _: deps.CurrentDevice
) -> schemas.FavoriteResponse:
    return library.put_favorite(item_id, payload)
