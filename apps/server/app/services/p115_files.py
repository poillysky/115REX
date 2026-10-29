"""115 网盘文件浏览（列目录 / 新建 / 重命名 / 删除 / 打开）。

令牌只经 p115_auth.access_token 取用，绝不投影到响应。
"""

from __future__ import annotations

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.integrations.p115 import DriveEntry, P115TransportError
from app.services import p115_auth


def _token(user_id: str) -> str:
    token = p115_auth.access_token(user_id)
    if not token:
        raise ApiError(409, ErrorCode.STORAGE_AUTH_REQUIRED, "请先绑定 115 网盘")
    return token


def _client():
    return p115_auth._client()  # noqa: SLF001 — 与扫码共用同一出口代理


def _map_entry(entry: DriveEntry) -> schemas.DriveEntryView:
    return schemas.DriveEntryView(
        id=entry.id,
        parentId=entry.parent_id,
        name=entry.name,
        isDir=entry.is_dir,
        size=entry.size,
        modifiedAt=entry.modified_at,
        extension=entry.extension,
        pickCode=entry.pick_code,
        thumbUrl=entry.thumb_url,
        previewUrl=entry.preview_url,
    )


def _raise_upstream(exc: P115TransportError) -> None:
    if exc.unauthorized:
        raise ApiError(409, ErrorCode.STORAGE_AUTH_REQUIRED, "115 授权已失效，请重新绑定") from exc
    raise ApiError(502, ErrorCode.UPSTREAM_ERROR, str(exc) or "115 请求失败") from exc


def list_files(
    user_id: str,
    *,
    cid: str = "0",
    offset: int = 0,
    limit: int = 200,
    order: str = "user_utime",
    asc: bool = False,
) -> schemas.DriveListingView:
    token = _token(user_id)
    try:
        listing = _client().list_files(
            token,
            cid=cid or "0",
            offset=offset,
            limit=limit,
            order=order,
            asc=asc,
        )
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    return schemas.DriveListingView(
        cid=listing.cid,
        count=listing.count,
        offset=listing.offset,
        limit=listing.limit,
        entries=[_map_entry(item) for item in listing.entries],
        path=[schemas.DrivePathNodeView(cid=node.cid, name=node.name) for node in listing.path],
    )


def mkdir(user_id: str, *, parent_id: str, name: str) -> schemas.DriveEntryView:
    token = _token(user_id)
    try:
        entry = _client().create_folder(token, parent_id=parent_id or "0", name=name)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    return _map_entry(entry)


def rename(user_id: str, *, file_id: str, name: str) -> None:
    token = _token(user_id)
    try:
        _client().rename_entry(token, file_id=file_id, name=name)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise


def delete(user_id: str, *, file_ids: list[str]) -> None:
    token = _token(user_id)
    try:
        _client().delete_entries(token, file_ids=file_ids)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise


def open_file(
    user_id: str,
    *,
    pick_code: str,
    extension: str = "",
    name: str = "",
) -> schemas.DriveOpenView:
    token = _token(user_id)
    try:
        result = _client().open_entry(
            token,
            pick_code=pick_code,
            extension=extension,
            name=name,
        )
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise
    return schemas.DriveOpenView(
        kind=result.kind,
        url=result.url,
        name=result.name,
        mimeHint=result.mime_hint,
    )


def download_url(user_id: str, *, pick_code: str) -> tuple[str, str]:
    """取直链，供流式代理使用。"""
    token = _token(user_id)
    try:
        return _client().download_url(token, pick_code=pick_code)
    except P115TransportError as exc:
        _raise_upstream(exc)
        raise

