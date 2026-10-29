"""v1 路由聚合。新增模块在这里挂一行。"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import assets, auth, library, meta, plugins, preferences, search, sites, storage

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(storage.router)
api_router.include_router(search.router)
api_router.include_router(library.router)
api_router.include_router(meta.router)
api_router.include_router(preferences.router)
api_router.include_router(sites.router)
api_router.include_router(plugins.router)
api_router.include_router(assets.router)
