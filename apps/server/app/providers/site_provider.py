"""站点资源源：把用户配置的 PT 站点接进聚合搜索。

一个站点一个 provider（id 形如 `site-<站点ID>`），按账号隔离：
站点增删改后由 `rebuild()` 重建注册表，保证搜索只看到当前账号的站点。

下载链接带个人 passkey，因此候选只提供 `download` 动作（推 qBittorrent），
不做 115 转存。具体请求与解析见 `services/site_spider.py`。
"""

from __future__ import annotations

import httpx
from sqlalchemy.orm import Session

from app.api import schemas
from app.providers.base import ProviderRegistry, SearchQuery, registry
from app.services import site_spider
from app.storage.db import SessionLocal
from app.storage.models import Site

# 搜索页体积通常几十到几百 KB，给宽松上限避免拖垮内存
_MAX_PAGE_BYTES = 8 * 1024 * 1024
_DEFAULT_UA = "Mozilla/5.0 (compatible; 115REX/0.1)"


class SiteError(Exception):
    """取种子失败。文案直接给用户看，所以要说清是哪一步出的问题。"""


def _headers(site: Site) -> dict[str, str]:
    headers = {"User-Agent": (site.ua or "").strip() or _DEFAULT_UA}
    cookie = (site.cookie or "").strip()
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _client(site: Site, timeout: int) -> httpx.AsyncClient:
    """站点代理开关决定是否走系统代理（翻墙站需要，内网站不需要）。"""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(float(timeout), connect=5.0),
        follow_redirects=True,
        trust_env=bool(site.proxy),
    )


class SiteProvider:
    """单个站点的搜索实现。站点字段在构造时拷出，避免跨线程持有 ORM 对象。"""

    def __init__(self, row: Site) -> None:
        self.id = f"site-{row.id}"
        self.name = row.name
        self.capability: schemas.ProviderCapability = "direct"
        self.enabled = bool(row.is_active)
        self.base_url = (row.url or "").strip()
        self.cookie = (row.cookie or "").strip()
        self.ua = (row.ua or "").strip()
        self.proxy = bool(row.proxy)
        self.timeout = max(3, min(int(row.timeout or 15), 60))
        self.public = bool(row.public)

    @property
    def ready(self) -> bool:
        """私有站没有 Cookie 搜不了；公开站不强制。"""
        return bool(self.base_url) and (self.public or bool(self.cookie))

    def _download_state(self) -> tuple[bool, str | None]:
        if not (self.cookie or self.public):
            return False, "站点未配置 Cookie，无法获取带 passkey 的种子"
        return True, None

    async def search(self, query: SearchQuery) -> list[schemas.CandidateView]:
        if not self.ready:
            return []
        keyword = (query.text or "").strip()
        if not keyword:
            return []
        url = site_spider.build_search_url(self.base_url, keyword)
        headers = {"User-Agent": self.ua or _DEFAULT_UA, "Cookie": self.cookie}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(float(self.timeout), connect=5.0),
            follow_redirects=True,
            trust_env=self.proxy,
        ) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text[:_MAX_PAGE_BYTES]

        available, reason = self._download_state()
        site_id = int(self.id.removeprefix("site-"))
        return [
            site_spider.to_candidate(
                torrent,
                site_id=site_id,
                site_name=self.name,
                download_available=available,
                download_reason=reason,
            )[0]
            for torrent in site_spider.parse_torrent_list(html, self.base_url)
        ]


def load_site(site_id: int, user_pk: int | None = None) -> Site | None:
    """按 ID 取站点；给了 user_pk 就顺带校验归属，供下载动作回找站点用。"""
    with SessionLocal() as db:
        query = db.query(Site).filter(Site.id == site_id)
        if user_pk is not None:
            query = query.filter(Site.user_id == user_pk)
        row = query.one_or_none()
        if row is None:
            return None
        # 提前把字段读出来，会话关闭后仍可用
        db.expunge(row)
        return row


def rebuild(user_pk: int, target: ProviderRegistry | None = None) -> None:
    """按账号重建该账号的站点源。调用点：启动、站点增删改、Cookie 变更。

    只动本账号名下的 `site-*`，避免多账号时互相清空。
    """
    pool = target or registry
    with SessionLocal() as db:
        rows = db.query(Site).filter(Site.user_id == user_pk).all()
    owned = {f"site-{row.id}" for row in rows}
    for provider in pool.all():
        if provider.id.startswith("site-") and provider.id in owned:
            pool.unregister(provider.id)
    # 已删除的站点不会再出现在 rows 里，兜底清掉所有指向不存在站点的注册
    alive = _all_site_ids()
    for provider in pool.all():
        if provider.id.startswith("site-") and _site_id(provider.id) not in alive:
            pool.unregister(provider.id)
    for row in rows:
        provider = SiteProvider(row)
        if provider.ready:
            pool.register(provider)


def _site_id(provider_id: str) -> int:
    try:
        return int(provider_id.removeprefix("site-"))
    except ValueError:
        return -1


def _all_site_ids() -> set[int]:
    with SessionLocal() as db:
        return {int(value) for (value,) in db.query(Site.id).all()}


def rebuild_all() -> None:
    """启动时把所有账号的站点都登记上（单机部署，账号很少）。"""
    with SessionLocal() as db:
        user_ids = [int(value) for (value,) in db.query(Site.user_id).distinct().all()]
    for user_pk in user_ids:
        rebuild(user_pk)


def resolve_ref(ref: str) -> tuple[int, str] | None:
    """把候选 ref（`站点ID:种子ID`）拆回站点与种子。"""
    site_id, _, torrent_id = ref.partition(":")
    if not site_id.isdigit() or not torrent_id:
        return None
    return int(site_id), torrent_id


async def fetch_torrent(site_id: int, torrent_id: str, user_pk: int) -> tuple[str, bytes | None]:
    """取种子：能直接拿到 .torrent 本体就返回文件，否则退回让下载器按链接取。

    返回 (下载链接, 文件内容)。文件为 None 时由 qBittorrent 自己请求该链接
    （链接已带上站点的 passkey，因此分享率照样计入）。
    """
    row = load_site(site_id, user_pk)
    if row is None:
        raise SiteError("站点不存在或已被删除")
    base_url = (row.url or "").strip()
    if not base_url:
        raise SiteError("站点地址为空，请先在站点设置里补充")
    passkey = (row.apikey or "").strip()
    download_url = site_spider.apply_passkey(
        f"{base_url.rstrip('/')}/download.php?id={torrent_id}", passkey
    )
    try:
        async with _client(row, max(3, min(int(row.timeout or 15), 60))) as client:
            response = await client.get(download_url, headers=_headers(row))
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SiteError(f"取种子失败：{exc}") from exc
    body = response.content
    # 标准 bencode 以 d 开头，说明站点直接回了 .torrent 本体
    if body[:1] == b"d":
        return download_url, body
    return download_url, None


__all__ = [
    "SiteError",
    "SiteProvider",
    "rebuild",
    "rebuild_all",
    "resolve_ref",
    "fetch_torrent",
    "load_site",
]
