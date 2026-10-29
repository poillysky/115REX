"""豆瓣 Frodo 出站客户端：热门墙与详情所需的最小子集。

签名协议对齐 MoviePilot `modules/douban/apiv2.py` 的公开 Frodo 约定。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import random
from datetime import datetime
from typing import Any
from urllib.parse import quote, urlparse

import httpx

_TIMEOUT = 20.0
_BASE = "https://frodo.douban.com/api/v2"
_API_KEY = "0dad551ec0f84ed02907ff5c42e8ec70"
_API_SECRET = "bf7dddc7c9cfe6f7"
_USER_AGENTS = (
    "api-client/1 com.douban.frodo/7.18.0(230) Android/22 product/MI 9 vendor/Xiaomi "
    "model/MI 9 brand/Android  rom/miui6  network/wifi  platform/mobile nd/1",
    "api-client/1 com.douban.frodo/7.3.0(207) Android/22 product/MI 9 vendor/Xiaomi "
    "model/MI 9 brand/Android  rom/miui6  network/wifi platform/mobile nd/1",
)

_URLS = {
    "movie_hot": "/subject_collection/movie_hot_gaia/items",
    "tv_hot": "/subject_collection/tv_hot/items",
    "movie_showing": "/subject_collection/movie_showing/items",
    "tv_animation": "/subject_collection/tv_animation/items",
    "movie_detail": "/movie/",
    "tv_detail": "/tv/",
    "movie_celebrities": "/movie/%s/celebrities",
    "tv_celebrities": "/tv/%s/celebrities",
}


class DoubanTransportError(RuntimeError):
    """豆瓣不可达或返回失败。"""


class DoubanClient:
    def __init__(self, *, proxy: str | None = None) -> None:
        self._proxy = (proxy or "").strip() or None

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=_TIMEOUT,
            trust_env=False,
            proxy=self._proxy,
            follow_redirects=True,
        )

    @staticmethod
    def _sign(url: str, ts: str, method: str = "GET") -> str:
        path = urlparse(url).path
        raw = "&".join([method.upper(), quote(path, safe=""), ts])
        digest = hmac.new(_API_SECRET.encode(), raw.encode(), hashlib.sha1).digest()
        return base64.b64encode(digest).decode()

    def _get(self, path: str, **params: Any) -> dict[str, Any]:
        req_url = f"{_BASE}{path}"
        ts = str(params.pop("_ts", datetime.strftime(datetime.now(), "%Y%m%d")))
        query: dict[str, Any] = {
            "apiKey": _API_KEY,
            "os_rom": "android",
            "_ts": ts,
            "_sig": self._sign(req_url, ts),
        }
        query.update(params)
        try:
            with self._client() as client:
                response = client.get(
                    req_url,
                    params=query,
                    headers={"User-Agent": random.choice(_USER_AGENTS)},
                )
        except httpx.HTTPError as exc:
            raise DoubanTransportError(f"无法连接豆瓣：{exc}") from exc
        if response.status_code >= 400:
            raise DoubanTransportError(f"豆瓣返回 {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise DoubanTransportError("豆瓣返回的不是 JSON") from exc
        if not isinstance(payload, dict):
            return {}
        if payload.get("code") not in (None, 0, "0") and payload.get("msg"):
            raise DoubanTransportError(str(payload.get("msg") or "豆瓣请求失败"))
        return payload

    def hot(self, kind: str, *, start: int = 0, count: int = 20) -> dict[str, Any]:
        key = "movie_hot" if kind == "movie" else "tv_hot"
        return self._get(_URLS[key], start=max(start, 0), count=max(count, 1))

    def showing(self, *, start: int = 0, count: int = 20) -> dict[str, Any]:
        return self._get(_URLS["movie_showing"], start=max(start, 0), count=max(count, 1))

    def animation(self, *, start: int = 0, count: int = 20) -> dict[str, Any]:
        return self._get(_URLS["tv_animation"], start=max(start, 0), count=max(count, 1))

    def detail(self, kind: str, subject_id: str) -> dict[str, Any]:
        prefix = _URLS["movie_detail"] if kind == "movie" else _URLS["tv_detail"]
        return self._get(f"{prefix}{subject_id}")

    def celebrities(self, kind: str, subject_id: str) -> dict[str, Any]:
        template = _URLS["movie_celebrities"] if kind == "movie" else _URLS["tv_celebrities"]
        return self._get(template % subject_id)


def cover_url(payload: dict[str, Any] | None) -> str | None:
    """从豆瓣条目里抠出海报地址。"""
    if not isinstance(payload, dict):
        return None
    for key in ("pic", "cover", "cover_url", "image"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
        if isinstance(value, dict):
            for nested in ("normal", "large", "url"):
                candidate = value.get(nested)
                if isinstance(candidate, str) and candidate.startswith("http"):
                    return candidate
    return None
