"""网盘绑定状态（docs/07 §2.2）+ 115 文件浏览。

只读状态 / 扫码授权 / 列目录与基础文件操作；响应不含任何凭据。
视频 / 大文件经本服务带 115 所需 UA 转发，浏览器不能直连 CDN。
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Header, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.api import deps, schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.services import auth, p115_auth, p115_files, p115_offline

router = APIRouter(prefix="/storage", tags=["storage"])

_STREAM_UA = "W115Storage/2.0"


def _user_id(claim: deps.CurrentClaim) -> str:
    """绑定是账号级资源，用令牌里的 user_id，而不是设备。"""
    return str(claim.get("sub") or "")


def _claim_from_header_or_query(
    authorization: str | None,
    access_token: str | None,
) -> dict:
    """<video> 无法带 Authorization，允许用查询参数 accessToken。"""
    raw = ""
    if authorization and authorization.lower().startswith("bearer "):
        raw = authorization.split(" ", 1)[1].strip()
    elif access_token:
        raw = access_token.strip()
    if not raw:
        raise ApiError(401, ErrorCode.TOKEN_MISSING, "请先登录")
    return auth.decode_access(raw)

@router.get("/bindings", response_model=schemas.StorageBindingsResponse)
def list_bindings(claim: deps.CurrentClaim) -> schemas.StorageBindingsResponse:
    return p115_auth.bindings(_user_id(claim))


@router.post("/115/auth/start", response_model=schemas.P115AuthStartView)
def start_p115_auth(claim: deps.CurrentClaim) -> schemas.P115AuthStartView:
    """申请扫码登录，返回二维码内容由前端渲染。"""
    return p115_auth.start(_user_id(claim))


@router.post("/115/auth/poll", response_model=schemas.P115AuthPollView)
def poll_p115_auth(
    payload: schemas.P115AuthPollRequest, claim: deps.CurrentClaim
) -> schemas.P115AuthPollView:
    """轮询一次扫码结果。前端按 retryAfter 秒后再来。"""
    return p115_auth.poll(_user_id(claim), payload.sessionId)


@router.post("/115/auth/unbind", response_model=schemas.StorageBindingsResponse)
def unbind_p115(claim: deps.CurrentClaim) -> schemas.StorageBindingsResponse:
    """解绑，清空该账号的 115 凭据。"""
    return p115_auth.unbind(_user_id(claim))


@router.get("/115/files", response_model=schemas.DriveListingView)
def list_drive_files(
    claim: deps.CurrentClaim,
    cid: Annotated[str, Query(description="目录 id，根为 0")] = "0",
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    order: Annotated[str, Query(description="file_name | file_size | user_utime")] = "user_utime",
    asc: Annotated[bool, Query(description="升序")] = False,
) -> schemas.DriveListingView:
    """列一层网盘目录，含面包屑。"""
    return p115_files.list_files(
        _user_id(claim),
        cid=cid,
        offset=offset,
        limit=limit,
        order=order,
        asc=asc,
    )


@router.post("/115/files/mkdir", response_model=schemas.DriveEntryView)
def mkdir_drive(
    payload: schemas.DriveMkdirRequest, claim: deps.CurrentClaim
) -> schemas.DriveEntryView:
    return p115_files.mkdir(_user_id(claim), parent_id=payload.parentId, name=payload.name)


@router.post("/115/files/rename", status_code=204, response_class=Response)
def rename_drive(payload: schemas.DriveRenameRequest, claim: deps.CurrentClaim) -> Response:
    p115_files.rename(_user_id(claim), file_id=payload.fileId, name=payload.name)
    return Response(status_code=204)


@router.post("/115/files/delete", status_code=204, response_class=Response)
def delete_drive(payload: schemas.DriveDeleteRequest, claim: deps.CurrentClaim) -> Response:
    p115_files.delete(_user_id(claim), file_ids=payload.fileIds)
    return Response(status_code=204)


@router.post("/115/files/open", response_model=schemas.DriveOpenView)
def open_drive_file(
    payload: schemas.DriveOpenRequest, claim: deps.CurrentClaim
) -> schemas.DriveOpenView:
    """签发图片 / 视频打开地址（短时直链，不含账号凭据）。"""
    return p115_files.open_file(
        _user_id(claim),
        pick_code=payload.pickCode,
        extension=payload.extension,
        name=payload.name,
    )


def _guess_media_type(file_name: str, upstream_type: str | None) -> str:
    """上游常回 application/octet-stream，按扩展名补浏览器可识别的类型。"""
    raw = (upstream_type or "").split(";", 1)[0].strip().lower()
    if raw and raw not in {"application/octet-stream", "binary/octet-stream"}:
        return upstream_type or raw
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    mapping = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "mov": "video/quicktime",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
        "pdf": "application/pdf",
        "txt": "text/plain; charset=utf-8",
        "md": "text/plain; charset=utf-8",
        "json": "application/json; charset=utf-8",
        "xml": "application/xml; charset=utf-8",
        "csv": "text/csv; charset=utf-8",
        "srt": "text/plain; charset=utf-8",
        "ass": "text/plain; charset=utf-8",
        "vtt": "text/vtt; charset=utf-8",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "svg": "image/svg+xml",
    }
    return mapping.get(ext, upstream_type or "application/octet-stream")


@router.get("/115/offline/quota", response_model=schemas.OfflineQuotaView)
def offline_quota(claim: deps.CurrentClaim) -> schemas.OfflineQuotaView:
    """云下载本月配额。"""
    return p115_offline.quota(_user_id(claim))


@router.get("/115/offline/summary", response_model=schemas.OfflineSummaryView)
def offline_summary(claim: deps.CurrentClaim) -> schemas.OfflineSummaryView:
    """配额 + 各状态任务数（会拉取全量任务并短时缓存）。"""
    return p115_offline.summary(_user_id(claim))


@router.get("/115/offline/tasks", response_model=schemas.OfflineTaskListView)
def offline_tasks(
    claim: deps.CurrentClaim,
    page: Annotated[int, Query(ge=1)] = 1,
    pageSize: Annotated[int, Query(ge=1, le=100)] = 30,
    status: Annotated[
        str | None,
        Query(description="all | downloading | failed | finished"),
    ] = None,
) -> schemas.OfflineTaskListView:
    """云下载任务列表。status 非空时服务端过滤并分页。"""
    return p115_offline.list_tasks(
        _user_id(claim),
        page=page,
        page_size=pageSize,
        status=status,
    )


@router.post("/115/offline/tasks", response_model=schemas.OfflineAddResponse)
def offline_add_tasks(
    payload: schemas.OfflineAddRequest, claim: deps.CurrentClaim
) -> schemas.OfflineAddResponse:
    """添加 HTTP/HTTPS/FTP/磁力/电驴链接任务。"""
    return p115_offline.add_urls(
        _user_id(claim),
        urls=payload.urls,
        wp_path_id=payload.wpPathId or "0",
    )


@router.post("/115/offline/tasks/delete", status_code=204, response_class=Response)
def offline_delete_task(
    payload: schemas.OfflineDeleteRequest, claim: deps.CurrentClaim
) -> Response:
    """删除云下载任务。"""
    p115_offline.delete_task(
        _user_id(claim),
        info_hash=payload.infoHash,
        del_source_file=payload.delSourceFile,
    )
    return Response(status_code=204)


@router.get("/115/files/stream")
def stream_drive_file(
    request: Request,
    pick_code: Annotated[str, Query(alias="pickCode", min_length=1)],
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query(alias="accessToken")] = None,
) -> StreamingResponse:
    """带 115 所需 User-Agent 转发直链，支持 Range，供预览使用。"""
    claim = _claim_from_header_or_query(authorization, access_token)
    user_id = str(claim.get("sub") or "")
    url, file_name = p115_files.download_url(user_id, pick_code=pick_code)

    upstream_headers = {"User-Agent": _STREAM_UA, "Accept": "*/*"}
    range_header = request.headers.get("range")
    if range_header:
        upstream_headers["Range"] = range_header

    proxy = get_settings().storage_proxy.strip() or None
    client = httpx.Client(
        proxy=proxy,
        timeout=httpx.Timeout(20.0, read=None),
        follow_redirects=True,
        trust_env=False,
    )
    try:
        upstream = client.send(
            client.build_request("GET", url, headers=upstream_headers),
            stream=True,
        )
    except httpx.HTTPError as exc:
        client.close()
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "无法连接文件源") from exc

    if upstream.status_code >= 400:
        upstream.close()
        client.close()
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "文件源拒绝了本次请求")

    def body() -> Iterator[bytes]:
        try:
            yield from upstream.iter_bytes(chunk_size=64 * 1024)
        finally:
            upstream.close()
            client.close()

    media = _guess_media_type(file_name, upstream.headers.get("content-type"))
    out: dict[str, str] = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=60",
        "Content-Type": media,
    }
    if file_name:
        out["Content-Disposition"] = f"inline; filename*=UTF-8''{quote(file_name)}"
    content_length = upstream.headers.get("content-length")
    if content_length:
        out["Content-Length"] = content_length
    content_range = upstream.headers.get("content-range")
    if content_range:
        out["Content-Range"] = content_range

    return StreamingResponse(
        body(),
        status_code=upstream.status_code,
        media_type=media,
        headers=out,
    )
