"""元数据发现与详情（TMDB / 豆瓣）。"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response

from app.api import deps, schemas
from app.services import meta, meta_image

router = APIRouter(prefix="/meta", tags=["meta"])


def _user_id(claim: deps.CurrentClaim) -> str:
    return str(claim.get("sub") or "")


@router.get("/img")
def proxy_image(request: Request, u: Annotated[str, Query(min_length=8)]) -> Response:
    """海报代理（无需登录）：解决豆瓣等防盗链，仅允许白名单域名。"""
    return meta_image.fetch_image(u, request)


@router.get("/boards", response_model=schemas.MetaBoardsResponse)
def list_boards(claim: deps.CurrentClaim) -> schemas.MetaBoardsResponse:
    """推荐首页：流行趋势 / 正在热映 / 热门电影等横滑榜单。"""
    return meta.boards(_user_id(claim))


@router.get("/discover", response_model=schemas.MetaDiscoverResponse)
def discover(
    claim: deps.CurrentClaim,
    source: Annotated[Literal["themoviedb", "douban"], Query()] = "themoviedb",
    kind: Annotated[Literal["movie", "tv"], Query()] = "movie",
    category: Annotated[str, Query()] = "",
    page: Annotated[int, Query(ge=1, le=50)] = 1,
) -> schemas.MetaDiscoverResponse:
    return meta.discover(
        _user_id(claim), source=source, kind=kind, page=page, category=category
    )


@router.get("/{source}/{media_id}", response_model=schemas.MetaDetailView)
def detail(
    source: Literal["themoviedb", "douban"],
    media_id: str,
    claim: deps.CurrentClaim,
    kind: Annotated[Literal["movie", "tv"], Query()] = "movie",
) -> schemas.MetaDetailView:
    return meta.detail(_user_id(claim), source=source, media_id=media_id, kind=kind)
