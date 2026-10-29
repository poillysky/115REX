"""聚合搜索与资源动作（docs/07 §2.3、§2.4）。

搜索返回两层结构 + 显式 partial；单源失败不作为 HTTP 错误。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api import deps, schemas
from app.errors import ApiError, ErrorCode
from app.services import actions, demo_data, health, search

router = APIRouter(tags=["search"])


@router.get("/search", response_model=schemas.SearchResponse)
async def search_endpoint(
    _: deps.CurrentDevice,
    q: Annotated[str, Query(min_length=1, description="查询词")],
    providers: Annotated[str | None, Query(description="来源过滤，逗号分隔")] = None,
    kind: Annotated[str | None, Query(description="movie / series")] = None,
    year: Annotated[int | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
) -> schemas.SearchResponse:
    provider_list = [item.strip() for item in providers.split(",")] if providers else None
    _ = (kind, year, cursor)  # 契约已预留，首版仅透传
    return await search.search(q, provider_list)


@router.get("/search/providers", response_model=schemas.ProvidersResponse)
def list_providers(_: deps.CurrentDevice) -> schemas.ProvidersResponse:
    from app.config import get_settings

    if get_settings().mock_mode:
        return schemas.ProvidersResponse(providers=demo_data.providers())
    return schemas.ProvidersResponse(providers=health.provider_views())


@router.get("/resources/{provider}/{ref}", response_model=schemas.CandidateDetailResponse)
def candidate_detail(
    provider: str, ref: str, _: deps.CurrentDevice
) -> schemas.CandidateDetailResponse:
    candidate = demo_data.find_candidate(provider, ref)
    if candidate is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "该候选已失效，请重新搜索")
    return schemas.CandidateDetailResponse(
        candidate=candidate,
        description=None,
        files=[candidate.title],
    )


@router.post(
    "/resources/{provider}/{ref}/actions",
    response_model=schemas.ActionAcceptedResponse,
    status_code=202,
)
def create_action(
    provider: str, ref: str, payload: schemas.ActionRequest, claim: deps.CurrentClaim
) -> schemas.ActionAcceptedResponse:
    return actions.create(
        provider, ref, payload.kind, payload.targetDir, str(claim.get("sub") or "")
    )


@router.get("/actions", response_model=schemas.ActionListResponse)
def list_actions(_: deps.CurrentDevice, page: deps.Pagination) -> schemas.ActionListResponse:
    limit, cursor = page
    return actions.list_all(cursor, limit)


@router.get("/actions/{action_id}", response_model=schemas.ActionView)
def get_action(action_id: str, _: deps.CurrentDevice) -> schemas.ActionView:
    return actions.get(action_id)
