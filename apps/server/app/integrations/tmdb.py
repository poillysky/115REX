"""TMDB 出站客户端：发现墙与详情所需的最小子集。

不移植完整识别/刮削链；只覆盖 trending + movie/tv detail（含 credits）。
"""

from __future__ import annotations

from typing import Any

import httpx

_TIMEOUT = 20.0
_DEFAULT_DOMAIN = "api.themoviedb.org"
_IMAGE_BASE = "https://image.tmdb.org/t/p"


class TmdbTransportError(RuntimeError):
    """TMDB 不可达或返回非业务成功状态。"""

    def __init__(self, message: str, *, unauthorized: bool = False) -> None:
        super().__init__(message)
        self.unauthorized = unauthorized


class TmdbClient:
    def __init__(
        self,
        api_key: str,
        *,
        proxy: str | None = None,
        language: str = "zh-CN",
        domain: str = _DEFAULT_DOMAIN,
    ) -> None:
        self._api_key = api_key.strip()
        self._proxy = (proxy or "").strip() or None
        self._language = language
        self._base = f"https://{domain.rstrip('/')}/3"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=_TIMEOUT,
            trust_env=False,
            proxy=self._proxy,
            follow_redirects=True,
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = {"api_key": self._api_key, "language": self._language}
        if params:
            query.update(params)
        try:
            with self._client() as client:
                response = client.get(f"{self._base}{path}", params=query)
        except httpx.HTTPError as exc:
            raise TmdbTransportError(f"无法连接 TMDB：{exc}") from exc
        if response.status_code in (401, 403):
            raise TmdbTransportError("TMDB API Key 无效或权限不足", unauthorized=True)
        if response.status_code >= 400:
            raise TmdbTransportError(f"TMDB 返回 {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise TmdbTransportError("TMDB 返回的不是 JSON") from exc
        return payload if isinstance(payload, dict) else {}

    def trending(self, kind: str, page: int = 1) -> dict[str, Any]:
        media = "movie" if kind == "movie" else "tv"
        return self._get(f"/trending/{media}/week", {"page": max(page, 1)})

    def trending_all(self, page: int = 1) -> dict[str, Any]:
        """流行趋势：电影 + 剧集混合。"""
        return self._get("/trending/all/week", {"page": max(page, 1)})

    def now_playing(self, page: int = 1) -> dict[str, Any]:
        return self._get("/movie/now_playing", {"page": max(page, 1)})

    def popular(self, kind: str, page: int = 1) -> dict[str, Any]:
        media = "movie" if kind == "movie" else "tv"
        return self._get(f"/{media}/popular", {"page": max(page, 1)})

    def detail(self, kind: str, media_id: str) -> dict[str, Any]:
        media = "movie" if kind == "movie" else "tv"
        return self._get(
            f"/{media}/{media_id}",
            {"append_to_response": "credits"},
        )


def poster_url(path: str | None, size: str = "w342") -> str | None:
    if not path or not isinstance(path, str):
        return None
    if path.startswith("http"):
        return path
    return f"{_IMAGE_BASE}/{size}{path}"


def backdrop_url(path: str | None, size: str = "w780") -> str | None:
    return poster_url(path, size=size)
