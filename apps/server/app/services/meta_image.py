"""元数据海报代理：对齐 MoviePilot 的图片代理思路。

相对原先实现的主要加速点：
1. 复用 httpx 连接池，不再每次新建 Client
2. 磁盘缓存 + ETag/304，重复打开几乎零上游请求
3. 豆瓣列表改用更小的 s_ratio_poster，适配横滑卡宽度
"""

from __future__ import annotations

import hashlib
import re
import threading
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import httpx
from fastapi import Request
from fastapi.responses import Response

from app.config import SERVER_ROOT, get_settings
from app.errors import ApiError, ErrorCode

_TIMEOUT = 12.0
_MAX_BYTES = 2 * 1024 * 1024
_CACHE_MAX_AGE = 86400 * 7
_ALLOWED_HOST_SUFFIXES = (
    "doubanio.com",
    "douban.com",
    "themoviedb.org",
    "tmdb.org",
    "image.tmdb.org",
)

# 列表卡约 132px 宽：豆瓣 s_ratio 足够；详情仍可用原图
_DOUBAN_LIST_SIZE = re.compile(r"/(?:m|l|raw)_ratio_poster/")

_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _cache_dir() -> Path:
    path = SERVER_ROOT / "data" / "meta-image-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def _shared_client(proxy: str | None) -> httpx.Client:
    """进程内复用连接，避免每张图握手一次。"""
    global _client
    with _client_lock:
        if _client is None:
            proxy_url = (proxy or get_settings().storage_proxy or "").strip() or None
            _client = httpx.Client(
                timeout=_TIMEOUT,
                follow_redirects=True,
                trust_env=False,
                proxy=proxy_url,
                limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                    ),
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                },
            )
        return _client


def shrink_douban_list_url(url: str) -> str:
    """列表展示降采样：m/l/raw → s_ratio_poster。"""
    if "doubanio.com" not in url:
        return url
    return _DOUBAN_LIST_SIZE.sub("/s_ratio_poster/", url)


def proxied_poster_url(url: str | None, *, list_size: bool = True) -> str | None:
    """豆瓣图改写成同源代理地址；其它原样返回。"""
    if not url or not isinstance(url, str):
        return None
    text = url.strip()
    if not text.startswith(("https://", "http://")):
        return text
    if "doubanio.com" not in text and "douban.com" not in text:
        return text
    if list_size:
        text = shrink_douban_list_url(text)
    return f"/api/v1/meta/img?u={quote(text, safe='')}"


def _read_cache(key: str) -> tuple[bytes, str] | None:
    meta = _cache_dir() / f"{key}.meta"
    blob = _cache_dir() / f"{key}.bin"
    if not meta.is_file() or not blob.is_file():
        return None
    try:
        content_type = meta.read_text(encoding="utf-8").strip() or "image/jpeg"
        body = blob.read_bytes()
    except OSError:
        return None
    if not body:
        return None
    return body, content_type


def _write_cache(key: str, body: bytes, content_type: str) -> None:
    try:
        folder = _cache_dir()
        (folder / f"{key}.bin").write_bytes(body)
        (folder / f"{key}.meta").write_text(content_type, encoding="utf-8")
    except OSError:
        pass


def fetch_image(url: str, request: Request | None = None) -> Response:
    text = unquote(url.strip())
    if not text.startswith(("https://", "http://")):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "图片地址无效")
    host = (urlparse(text).hostname or "").lower()
    if not any(host == s or host.endswith("." + s) for s in _ALLOWED_HOST_SUFFIXES):
        raise ApiError(400, ErrorCode.BAD_REQUEST, "不支持代理该图片域名")

    key = _cache_key(text)
    cached = _read_cache(key)
    if cached:
        body, content_type = cached
        etag = f'"{key}"'
        if_none_match = request.headers.get("if-none-match") if request else None
        headers = {
            "ETag": etag,
            "Cache-Control": f"public, max-age={_CACHE_MAX_AGE}",
            "X-Content-Type-Options": "nosniff",
            "X-Cache": "HIT",
        }
        if if_none_match == etag:
            return Response(status_code=304, headers=headers)
        return Response(content=body, media_type=content_type, headers=headers)

    referer = "https://movie.douban.com/" if "douban" in host else "https://www.themoviedb.org/"
    try:
        client = _shared_client(None)
        response = client.get(
            text,
            headers={
                "Referer": referer,
            },
        )
        response.raise_for_status()
        body = response.content
    except httpx.HTTPError as exc:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "封面图加载失败") from exc

    if not body or len(body) > _MAX_BYTES:
        raise ApiError(502, ErrorCode.UPSTREAM_ERROR, "封面图无效或过大")

    content_type = response.headers.get("content-type") or "image/jpeg"
    if ";" in content_type:
        content_type = content_type.split(";", 1)[0].strip()
    if not content_type.startswith("image/"):
        content_type = "image/jpeg"

    _write_cache(key, body, content_type)
    etag = f'"{key}"'
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "ETag": etag,
            "Cache-Control": f"public, max-age={_CACHE_MAX_AGE}",
            "X-Content-Type-Options": "nosniff",
            "X-Cache": "MISS",
        },
    )
