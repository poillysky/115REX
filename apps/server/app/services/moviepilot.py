"""MoviePilot 接入：只读状态，不干预它的自动化流程。

搜索、媒体识别、整理、加种全部由 MoviePilot 自己完成，本服务只负责
把它的运行概况拉过来给界面看，因此这里只调用查询类接口，不调用
`/download/add` 这类会改变对方状态的方法。

鉴权走 MoviePilot 的 `?token=<API_TOKEN>`，它等价超级用户权限。
"""

from __future__ import annotations

import asyncio
import time

import httpx

from app.api import schemas


class MoviepilotError(RuntimeError):
    """MoviePilot 不可达或返回了业务错误。"""


def _client(url: str, timeout: float = 10.0) -> httpx.AsyncClient:
    """MoviePilot 通常部署在内网，直连即可，不受系统代理影响。"""
    return httpx.AsyncClient(base_url=url.rstrip("/"), timeout=timeout, trust_env=False)


async def _get(client: httpx.AsyncClient, path: str, token: str) -> dict:
    """发一次 GET，把网络错误、HTTP 错误、`success=false` 统一转成 MoviepilotError。"""
    try:
        response = await client.get(path, params={"token": token})
    except httpx.HTTPError as exc:
        raise MoviepilotError(f"无法连接 MoviePilot：{exc}") from exc
    if response.status_code in (401, 403):
        raise MoviepilotError("MoviePilot 令牌无效或权限不足，请检查 API Token")
    if response.status_code >= 400:
        raise MoviepilotError(f"MoviePilot 返回 {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise MoviepilotError("MoviePilot 返回的不是 JSON，请确认地址填的是后端端口") from exc
    if isinstance(payload, dict) and payload.get("success") is False:
        raise MoviepilotError(str(payload.get("message") or "MoviePilot 返回失败"))
    return payload if isinstance(payload, dict) else {"data": payload}


def _downloaders(payload: dict) -> list[dict]:
    data = payload.get("data") or []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _bytes(value: object) -> int | None:
    """MoviePilot 的容量字段是浮点数，这里统一成整数字节。"""
    return int(value) if isinstance(value, (int, float)) else None


# 后台服务里用中文名判断失败项，避免把「等待中」误判成异常
_FAILED_STATUS = {"failed", "failure", "error"}


def _failed_jobs(payload: dict) -> tuple[list[schemas.MoviepilotJobView], int]:
    """挑出最近一次执行失败的后台服务。

    26 个后台服务里绝大多数是「等待」或「成功」，卡片上穷举没有意义，
    只把失败的挑出来；同时带回总数，方便确认对端确实在调度。
    """
    rows = payload.get("data") or []
    if not isinstance(rows, list):
        return [], 0
    failed: list[schemas.MoviepilotJobView] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        detail = row.get("progress_detail")
        detail = detail if isinstance(detail, dict) else {}
        status = str(detail.get("status") or "").lower()
        error = str(detail.get("error") or "")
        success = detail.get("success")
        if success is False or error or status in _FAILED_STATUS:
            failed.append(
                schemas.MoviepilotJobView(
                    id=str(row.get("id") or ""),
                    name=str(row.get("name_i18n") or row.get("name") or ""),
                    status=str(row.get("status_i18n") or row.get("status") or ""),
                    nextRun=str(row.get("next_run_i18n") or row.get("next_run") or ""),
                    ok=False if success is False else None,
                    error=error,
                    finishedAt=str(detail.get("finished_at") or ""),
                )
            )
    return failed, len(rows)


async def read_status(config: schemas.MoviepilotView) -> schemas.MoviepilotStatusView:
    """拉取站点清单、下载器清单与运行概况，用于卡片展示。

    站点清单只用来确认两边站点对得上，取不到不算致命；下载器清单取不到
    说明地址或令牌有问题，直接判成失败。
    """
    if not config.url:
        return schemas.MoviepilotStatusView(ok=False, message="尚未填写 MoviePilot 地址")
    if not config.token:
        return schemas.MoviepilotStatusView(ok=False, message="尚未填写 MoviePilot 令牌")

    started = time.perf_counter()
    async with _client(config.url) as client:
        # 站点接口仅用于确认两边站点名能对上，取不到也不算致命
        sites_task = asyncio.create_task(_get(client, "/api/v1/site/", config.token))
        clients_task = asyncio.create_task(
            _get(client, "/api/v1/download/clients", config.token)
        )
        try:
            clients_payload = await clients_task
        except MoviepilotError as exc:
            sites_task.cancel()
            return schemas.MoviepilotStatusView(ok=False, message=str(exc))

        try:
            sites_payload = await sites_task
        except MoviepilotError:
            sites_payload = {}

        downloaders = _downloaders(clients_payload)
        first = downloaders[0] if downloaders else {}
        downloader = str(first.get("name") or "")
        downloader_type = str(first.get("type") or "")

        status = schemas.MoviepilotStatusView(
            ok=True,
            message="" if downloader else "MoviePilot 里没有启用中的下载器",
            sites=[
                str(item.get("name"))
                for item in (sites_payload.get("data") or [])
                if isinstance(item, dict) and item.get("name")
            ],
            downloader=downloader,
            downloaderType=downloader_type,
            connectionStatus="connected" if downloader else "disconnected",
        )
        # 没有下载器时上述接口都会因缺少 name 而报错，没必要再问一次
        if downloader:
            await _fill_transfer(client, config.token, status)

    elapsed = time.perf_counter() - started
    if elapsed > 5:
        status.message = f"{status.message}（响应 {elapsed:.1f}s）".strip()
    return status


async def _fill_transfer(
    client: httpx.AsyncClient, token: str, status: schemas.MoviepilotStatusView
) -> None:
    """补齐速度、累计流量、磁盘容量与后台服务健康度。

    这几项互不依赖，并发取；其中任何一项失败都只留空，不把整体判成失败，
    否则下载器一时卡住会让整张卡片变红，掩盖「MoviePilot 本身是通的」。
    """
    paths = {
        "downloader": "/api/v1/dashboard/downloader",
        "storage": "/api/v1/dashboard/storage2",
        "schedule": "/api/v1/dashboard/schedule",
        "tasks": "/api/v1/download/",
    }
    results = await asyncio.gather(
        *(_get(client, path, token) for path in paths.values()), return_exceptions=True
    )
    payloads: dict[str, dict] = {}
    for (key, _), result in zip(paths.items(), results):
        if isinstance(result, dict):
            payloads[key] = result

    # 该接口返回单个对象；带 name 参数时才可能是按下载器分组的列表
    data = payloads.get("downloader", {}).get("data")
    rows = data if isinstance(data, list) else [data]
    for item in rows:
        if not isinstance(item, dict):
            continue
        dl = item.get("download_speed")
        up = item.get("upload_speed")
        status.dlSpeed = int(dl) if isinstance(dl, (int, float)) else 0
        status.upSpeed = int(up) if isinstance(up, (int, float)) else 0
        status.dlTotal = _bytes(item.get("download_size"))
        status.upTotal = _bytes(item.get("upload_size"))
        status.freeSpace = _bytes(item.get("free_space"))
        break

    # 下载器能返回速度说明链路真实可用，比「站点列表能取到」更能代表连通性
    if "downloader" in payloads:
        status.connectionStatus = "connected"

    storage = payloads.get("storage", {}).get("data")
    if isinstance(storage, dict):
        status.totalSpace = _bytes(storage.get("total_storage"))
        status.usedSpace = _bytes(storage.get("used_storage"))

    if "schedule" in payloads:
        status.jobs, status.jobTotal = _failed_jobs(payloads["schedule"])

    rows = payloads.get("tasks", {}).get("data") or []
    if isinstance(rows, list):
        status.activeTasks = sum(
            1
            for row in rows
            if isinstance(row, dict) and str(row.get("state") or "").startswith("download")
        )


async def test_connection(config: schemas.MoviepilotView) -> schemas.MoviepilotStatusView:
    """试连：只验证地址可通、令牌有效、能找到下载器，不落库。"""
    return await read_status(config)
