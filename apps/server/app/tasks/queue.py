"""任务队列（docs/06 §6）。

首版：进程内队列 + 单 worker，不引入 Celery / Redis。
tasks 层不直接写数据库，落库一律经由服务层。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

Handler = Callable[[str], Awaitable[None]]


@dataclass
class Job:
    queue: str  # action / probe / scrape / maintenance
    handler: Handler
    payload: str


class InProcessQueue:
    def __init__(self) -> None:
        self._jobs: asyncio.Queue[Job] = asyncio.Queue()
        self._worker: asyncio.Task[None] | None = None

    def submit(self, job: Job) -> None:
        self._jobs.put_nowait(job)

    async def _run(self) -> None:
        while True:
            job = await self._jobs.get()
            try:
                await job.handler(job.payload)
            except Exception:  # noqa: BLE001 — 单任务失败不能拖垮 worker
                logger.exception("task failed: queue=%s payload=%s", job.queue, job.payload)
            finally:
                self._jobs.task_done()

    def start(self) -> None:
        if self._worker is None:
            self._worker = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self._worker = None


queue = InProcessQueue()
