"""FastAPI 入口。

职责：装配路由、异常信封、静态托管、CORS、建表与任务队列。
启动：uvicorn app.main:app --reload --port 9959（在 apps/server 下）
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import get_settings
from app.errors import ApiError, ErrorCode, api_error_handler, unhandled_error_handler
from app.providers import site_provider
from app.providers.base import registry
from app.providers.mock import MockProvider
from app.storage import init_db
from app.tasks.queue import queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("rex")

MOCK_PROVIDERS = [
    ("local-pg", "自建资源库", "transfer"),
    ("bitmagnet", "BitMagnet", "direct"),
    ("cloudsaver", "CloudSaver", "transfer"),
    ("semitio", "semitio addon", "read_only"),
]


def _register_providers() -> None:
    settings = get_settings()
    if settings.mock_mode:
        for provider_id, name, capability in MOCK_PROVIDERS:
            registry.register(MockProvider(provider_id, name, capability))  # type: ignore[arg-type]
        return
    # 真实源接入：在这里 register 各自的实现类（docs/05 §8）
    # 用户配置的 PT 站点，一个站点一个源；站点增删改时由 services/sites 增量重建
    site_provider.rebuild_all()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    _register_providers()
    queue.start()
    logger.info("115REX server started (mock_mode=%s)", get_settings().mock_mode)
    yield
    await queue.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="115REX API",
        version="0.1.0",
        description="影视终端 + 资源整合搜索的控制面。契约见 docs/07-api-contract.md。",
        lifespan=lifespan,
    )

    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_error_handler)

    # 生产由后端同源托管 Web，正常不需要 CORS（docs/06 §8）
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix="/api/v1")

    static_dir = Path(settings.static_dir).resolve() if settings.static_dir else None
    if static_dir and (static_dir / "index.html").is_file():
        index_file = static_dir / "index.html"

        @app.get("/{full_path:path}", include_in_schema=False)
        def spa_fallback(full_path: str) -> FileResponse:
            """history 路由深链回退到 index.html（刷新 /system/sources 等不 404）。

            绝不吞掉 /api：接口未注册时应 404 JSON，而不是返回 HTML 让前端 JSON.parse 失败。
            """
            if full_path == "api" or full_path.startswith("api/"):
                raise ApiError(404, ErrorCode.NOT_FOUND, "接口不存在")
            candidate = (static_dir / full_path).resolve()
            if full_path and candidate.is_file() and candidate.is_relative_to(static_dir):
                return FileResponse(candidate)
            return FileResponse(index_file)

    return app


app = create_app()
