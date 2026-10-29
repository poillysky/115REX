"""市场插件图标：安装时下载到本地，列表只读本地文件，运行时不联网。"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import SERVER_ROOT, get_settings

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_MAX_BYTES = 512 * 1024
_TIMEOUT = 15.0

_EXT_BY_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
}

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def icons_dir() -> Path:
    path = SERVER_ROOT / "data" / "plugin-icons"
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_plugin_id(plugin_id: str) -> str:
    text = plugin_id.strip()
    if not _SAFE_ID.match(text):
        raise ValueError("插件 id 非法")
    return text


def local_icon_path(plugin_id: str) -> Path | None:
    """返回已落盘的图标文件；无则 None。"""
    try:
        pid = safe_plugin_id(plugin_id)
    except ValueError:
        return None
    matches = sorted(icons_dir().glob(f"{pid}.*"))
    return matches[0] if matches else None


def local_icon_url(plugin_id: str) -> str:
    """给前端 <img> 用的同源地址（无需 Bearer，文件本身不敏感）。"""
    return f"/api/v1/plugins/{plugin_id}/icon"


def remove_local_icon(plugin_id: str) -> None:
    try:
        pid = safe_plugin_id(plugin_id)
    except ValueError:
        return
    for path in icons_dir().glob(f"{pid}.*"):
        path.unlink(missing_ok=True)


def _guess_ext(url: str, content_type: str | None) -> str:
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime in _EXT_BY_MIME:
        return _EXT_BY_MIME[mime]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in _MIME_BY_EXT:
        return suffix
    return ".png"


def download_icon(plugin_id: str, remote_url: str, *, proxy: str | None = None) -> Path:
    """安装时拉取远程图标写到 data/plugin-icons/{id}.ext。"""
    pid = safe_plugin_id(plugin_id)
    url = remote_url.strip()
    if not url.startswith(("https://", "http://")):
        raise ValueError("图标地址必须以 http(s) 开头")

    remove_local_icon(pid)
    proxy_url = (proxy or get_settings().storage_proxy or "").strip() or None
    try:
        with httpx.Client(
            timeout=_TIMEOUT,
            follow_redirects=True,
            trust_env=False,
            proxy=proxy_url,
        ) as client:
            response = client.get(url, headers={"User-Agent": "115REX"})
            response.raise_for_status()
            body = response.content
            if not body:
                raise ValueError("图标内容为空")
            if len(body) > _MAX_BYTES:
                raise ValueError("图标过大")
            ext = _guess_ext(url, response.headers.get("content-type"))
    except httpx.HTTPError as exc:
        raise ValueError(f"图标下载失败：{exc}") from exc

    dest = icons_dir() / f"{pid}{ext}"
    dest.write_bytes(body)
    return dest


def media_type_for(path: Path) -> str:
    return _MIME_BY_EXT.get(path.suffix.lower(), "application/octet-stream")
