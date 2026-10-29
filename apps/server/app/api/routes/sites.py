"""站点管理：列表 / 增删改 / 导入 / 连通测试 / 统计 / 优先级。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Response

from app.api import deps, schemas
from app.services import sites

router = APIRouter(prefix="/sites", tags=["sites"])


def _user_id(claim: deps.CurrentClaim) -> str:
    return str(claim.get("sub") or "")


@router.get("", response_model=schemas.SiteListView)
def list_sites(claim: deps.CurrentClaim) -> schemas.SiteListView:
    return sites.list_sites(_user_id(claim))


@router.post("", response_model=schemas.SiteView, status_code=201)
def create_site(payload: schemas.SiteWrite, claim: deps.CurrentClaim) -> schemas.SiteView:
    return sites.create_site(_user_id(claim), payload)


@router.post("/import", response_model=schemas.SiteView, status_code=201)
def import_one_site(
    claim: deps.CurrentClaim, payload: dict[str, Any] = Body(...)
) -> schemas.SiteView:
    write = sites.site_write_from_import(payload)
    return sites.create_site(_user_id(claim), write)


@router.get("/statistics", response_model=schemas.SiteStatisticListView)
def list_statistics(claim: deps.CurrentClaim) -> schemas.SiteStatisticListView:
    return sites.list_statistics(_user_id(claim))


@router.get("/statistics/{domain}", response_model=schemas.SiteStatisticView)
def get_statistic(domain: str, claim: deps.CurrentClaim) -> schemas.SiteStatisticView:
    return sites.get_statistic(_user_id(claim), domain)


@router.put("/priorities", response_model=schemas.SiteListView)
def update_priorities(
    payload: schemas.SitePriorityUpdate, claim: deps.CurrentClaim
) -> schemas.SiteListView:
    return sites.update_priorities(_user_id(claim), payload.items)


@router.get("/meta", response_model=schemas.SiteMetaView)
def fetch_meta(
    url: str, claim: deps.CurrentClaim, ua: str = "", proxy: bool = False
) -> schemas.SiteMetaView:
    """按站点地址抓首页标题取站名，供添加站点时自动填入。不落库。"""
    return sites.fetch_site_meta(url, ua, proxy=proxy)


@router.get("/{site_id}", response_model=schemas.SiteView)
def get_site(site_id: int, claim: deps.CurrentClaim) -> schemas.SiteView:
    return sites.get_site(_user_id(claim), site_id)


@router.put("/{site_id}", response_model=schemas.SiteView)
def replace_site(
    site_id: int, payload: schemas.SiteWrite, claim: deps.CurrentClaim
) -> schemas.SiteView:
    return sites.update_site(_user_id(claim), site_id, payload)


@router.patch("/{site_id}", response_model=schemas.SiteView)
def patch_site(
    site_id: int, payload: schemas.SitePatch, claim: deps.CurrentClaim
) -> schemas.SiteView:
    return sites.patch_site(_user_id(claim), site_id, payload)


@router.get("/{site_id}/test", response_model=schemas.SiteTestResultView)
def test_site(site_id: int, claim: deps.CurrentClaim) -> schemas.SiteTestResultView:
    return sites.test_site(_user_id(claim), site_id)


@router.get("/{site_id}/probe", response_model=schemas.SiteProbeResultView)
async def probe_site(
    site_id: int,
    claim: deps.CurrentClaim,
    q: str = "1080p",
) -> schemas.SiteProbeResultView:
    """用关键词试搜一次，确认站点的搜索页能解析出种子。不落库、不计入统计。"""
    return await sites.probe_site(_user_id(claim), site_id, q)


@router.delete("/{site_id}", status_code=204)
def delete_site(site_id: int, claim: deps.CurrentClaim) -> Response:
    sites.delete_site(_user_id(claim), site_id)
    return Response(status_code=204)
