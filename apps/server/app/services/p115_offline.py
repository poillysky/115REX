"""115 云下载（配额 / 任务列表 / 添加链接 / 删除）。

开放接口不支持按状态筛选，也不宜连打多页（易触达限流）。
列表走 115 原生分页，再在当页按 status 过滤；全量缓存仅在 summary
主动触发时串行拉取，供 tab 精确计数。
"""

from __future__ import annotations

import threading
import time

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.integrations.p115 import OfflineTask, P115TransportError
from app.services import p115_auth

_CACHE_TTL_SECONDS = 90.0
# 限流窗口较长，少重试、多等待，避免越重试越触发
_RATE_LIMIT_SLEEP = 8.0
_RATE_LIMIT_RETRIES = 2

# user_id -> (expires_at, tasks)
_task_cache: dict[str, tuple[float, tuple[OfflineTask, ...]]] = {}
_cache_lock = threading.Lock()


def _token(user_id: str) -> str:
    token = p115_auth.access_token(user_id)
    if not token:
        raise ApiError(409, ErrorCode.STORAGE_AUTH_REQUIRED, "请先绑定 115 网盘")
    return token


def _client():
    return p115_auth._client()  # noqa: SLF001 — 与扫码共用同一出口代理


def _is_rate_limited(exc: P115TransportError) -> bool:
    message = str(exc)
    return any(token in message for token in ("上限", "频繁", "太多", "rate"))


def _raise_upstream(exc: P115TransportError) -> None:
    if exc.unauthorized:
        raise ApiError(409, ErrorCode.STORAGE_AUTH_REQUIRED, "115 授权已失效，请重新绑定") from exc
    if _is_rate_limited(exc):
        raise ApiError(
            429,
            ErrorCode.UPSTREAM_ERROR,
            "115 请求过于频繁，请稍后再试",
        ) from exc
    raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc) or "115 请求失败") from exc


def _map_task(task: OfflineTask) -> schemas.OfflineTaskView:
    return schemas.OfflineTaskView(
        infoHash=task.info_hash,
        name=task.name,
        size=task.size,
        addTime=task.add_time,
        status=task.status,
        statusText=task.status_text,
        percentDone=task.percent_done,
        url=task.url,
        fileId=task.file_id,
        pickCode=task.pick_code,
        wpPathId=task.wp_path_id,
        fileCategory=task.file_category,
        rateDownload=task.rate_download,
        leftTime=task.left_time,
    )


def _invalidate(user_id: str) -> None:
    with _cache_lock:
        _task_cache.pop(user_id, None)


def _task_page_with_retry(token: str, page: int):
    client = _client()
    last: P115TransportError | None = None
    for attempt in range(_RATE_LIMIT_RETRIES):
        try:
            return client.offline_task_page(token, page=page)
        except P115TransportError as exc:
            last = exc
            if _is_rate_limited(exc) and attempt + 1 < _RATE_LIMIT_RETRIES:
                time.sleep(_RATE_LIMIT_SLEEP * (attempt + 1))
                continue
            raise
    assert last is not None
    raise last


def _match_status(task: OfflineTask, status: str | None) -> bool:
    if not status or status == "all":
        return True
    key = status.strip().lower()
    if key in {"downloading", "active"}:
        return task.status in (0, 1)
    if key in {"failed", "fail", "error"}:
        return task.status == -1
    if key in {"finished", "done", "completed", "success"}:
        return task.status == 2
    try:
        return task.status == int(key)
    except ValueError:
        return True


def _status_counts_from(
    tasks: tuple[OfflineTask, ...] | list[OfflineTask],
    *,
    total_hint: int | None = None,
) -> schemas.OfflineStatusCountsView:
    downloading = 0
    failed = 0
    finished = 0
    for item in tasks:
        if item.status in (0, 1):
            downloading += 1
        elif item.status == -1:
            failed += 1
        elif item.status == 2:
            finished += 1
    if total_hint is not None and len(tasks) < total_hint:
        # 未拉全量时：用总数估完成数，下载中/失败仅反映已见样本
        finished = max(total_hint - downloading - failed, finished)
    return schemas.OfflineStatusCountsView(
        downloading=downloading,
        failed=failed,
        finished=finished,
        total=total_hint if total_hint is not None else len(tasks),
    )


def _cached_tasks(user_id: str) -> tuple[OfflineTask, ...] | None:
    with _cache_lock:
        cached = _task_cache.get(user_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]
    return None


def _fetch_all_tasks(user_id: str, token: str) -> tuple[OfflineTask, ...]:
    hit = _cached_tasks(user_id)
    if hit is not None:
        return hit

    try:
        first = _task_page_with_retry(token, 1)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise

    ordered: list[OfflineTask] = list(first.tasks)
    page_count = max(first.page_count, 1)
    for page in range(2, page_count + 1):
        try:
            chunk = _task_page_with_retry(token, page)
        except P115TransportError as exc:
            _raise_upstream(exc)
            raise
        ordered.extend(chunk.tasks)
        if page < page_count:
            time.sleep(0.35)

    result = tuple(ordered)
    with _cache_lock:
        _task_cache[user_id] = (time.monotonic() + _CACHE_TTL_SECONDS, result)
    return result


def quota(user_id: str) -> schemas.OfflineQuotaView:
    token = _token(user_id)
    try:
        info = _client().offline_quota(token)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    return schemas.OfflineQuotaView(surplus=info.surplus, used=info.used, count=info.count)


def list_tasks(
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 30,
    status: str | None = None,
) -> schemas.OfflineTaskListView:
    token = _token(user_id)
    page_no = max(1, int(page))
    size = max(1, min(int(page_size), 100))

    cached = _cached_tasks(user_id)
    if cached is not None:
        filtered = [item for item in cached if _match_status(item, status)]
        total = len(filtered)
        page_count = max((total + size - 1) // size, 1) if total else 1
        if page_no > page_count:
            page_no = page_count
        start = (page_no - 1) * size
        slice_tasks = filtered[start : start + size]
        return schemas.OfflineTaskListView(
            page=page_no,
            pageCount=page_count,
            count=total,
            pageSize=size,
            statusCounts=_status_counts_from(cached),
            tasks=[_map_task(item) for item in slice_tasks],
        )

    # 无缓存：单页原生拉取 + 当页过滤（不连扫，避开限流）
    try:
        raw = _task_page_with_retry(token, page_no)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise

    filtered = [item for item in raw.tasks if _match_status(item, status)]
    counts = _status_counts_from(raw.tasks, total_hint=raw.count)
    # 无全量时，当前 tab 的 count 用总量近似（完成）或当页样本
    if status == "finished":
        tab_count = counts.finished
    elif status == "failed":
        tab_count = counts.failed
    elif status == "downloading":
        tab_count = counts.downloading
    else:
        tab_count = raw.count

    return schemas.OfflineTaskListView(
        page=raw.page,
        pageCount=raw.page_count,
        count=tab_count,
        pageSize=size,
        statusCounts=counts,
        tasks=[_map_task(item) for item in filtered],
    )


def summary(user_id: str) -> schemas.OfflineSummaryView:
    token = _token(user_id)
    try:
        q = _client().offline_quota(token)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    tasks = _fetch_all_tasks(user_id, token)
    return schemas.OfflineSummaryView(
        quota=schemas.OfflineQuotaView(surplus=q.surplus, used=q.used, count=q.count),
        statusCounts=_status_counts_from(tasks),
    )


def add_urls(
    user_id: str,
    *,
    urls: list[str],
    wp_path_id: str = "0",
) -> schemas.OfflineAddResponse:
    token = _token(user_id)
    try:
        results = _client().offline_add_urls(token, urls=urls, wp_path_id=wp_path_id)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    _invalidate(user_id)
    return schemas.OfflineAddResponse(
        results=[
            schemas.OfflineAddResultView(
                url=item.url,
                infoHash=item.info_hash,
                name=item.name,
                ok=item.ok,
                message=item.message,
            )
            for item in results
        ]
    )


def delete_task(
    user_id: str,
    *,
    info_hash: str,
    del_source_file: bool = False,
) -> None:
    token = _token(user_id)
    try:
        _client().offline_del_task(
            token,
            info_hash=info_hash,
            del_source_file=del_source_file,
        )
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    _invalidate(user_id)
