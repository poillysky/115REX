"""qBittorrent WebUI 客户端。

PT 站点的下载链接带个人 passkey，只有把种子交给下载器才会累计分享率，
因此站点的资源统一推给 qBittorrent，而不是转存到网盘。

接口都是 WebUI 的 `/api/v2/*`：先 `auth/login` 拿 SID Cookie，后续请求带上它。
下载器一般跑在本机或局域网，出站**不走**代理（`trust_env=False`），
否则经过翻墙代理反而连不上内网地址。
"""

from __future__ import annotations

from typing import Any

import httpx

from app.api import schemas

# 登录与常规请求分开给超时：登录串行、其余多为小 JSON
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class QbittorrentError(Exception):
    """下载器返回非预期结果。调用方转成对外可读的提示。"""


class QbittorrentClient:
    """一个配置对应一个短生命周期客户端，用完即关，不共享连接池。"""

    def __init__(self, config: schemas.QbittorrentView) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "QbittorrentClient":
        self._client = httpx.AsyncClient(
            base_url=self.config.url.rstrip("/"),
            timeout=_TIMEOUT,
            trust_env=False,
            follow_redirects=True,
        )
        await self._login()
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise QbittorrentError("下载器连接尚未建立")
        return self._client

    async def _login(self) -> None:
        """登录成功返回 `200 Ok.`（旧版）或空的 `204`（4.1+），两种都要认。"""
        try:
            response = await self.client.post(
                "/api/v2/auth/login",
                data={"username": self.config.username, "password": self.config.password},
            )
        except httpx.HTTPError as exc:
            raise QbittorrentError(f"无法连接 qBittorrent：{exc}") from exc
        text = response.text.strip()
        if response.status_code not in (200, 204) or text.startswith("Fails"):
            raise QbittorrentError("qBittorrent 登录失败，请检查用户名与密码")

    async def version(self) -> str:
        try:
            response = await self.client.get("/api/v2/app/version")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise QbittorrentError(f"读取 qBittorrent 版本失败：{exc}") from exc
        return response.text.strip()

    async def add_urls(self, urls: list[str]) -> None:
        """按链接添加种子（支持 http 种子地址与磁力）。分类与保存路径取配置默认值。"""
        if not urls:
            return
        data: dict[str, str] = {"urls": "\n".join(urls)}
        if self.config.category:
            data["category"] = self.config.category
        if self.config.savePath:
            data["savepath"] = self.config.savePath
        try:
            response = await self.client.post("/api/v2/torrents/add", data=data)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise QbittorrentError(f"提交任务失败：{exc}") from exc
        # qB 在参数不合法时也返回 200，但正文是 Fails.，需要自行判断
        if response.text.strip().startswith("Fails"):
            raise QbittorrentError("qBittorrent 拒绝了该种子链接")

    async def add_file(self, filename: str, content: bytes) -> None:
        """上传 .torrent 文件本体，用于站点只返回附件、链接需要二次跳转的场景。"""
        data: dict[str, str] = {}
        if self.config.category:
            data["category"] = self.config.category
        if self.config.savePath:
            data["savepath"] = self.config.savePath
        try:
            response = await self.client.post(
                "/api/v2/torrents/add",
                data=data,
                files={"torrents": (filename or "upload.torrent", content, "application/x-bittorrent")},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise QbittorrentError(f"上传种子失败：{exc}") from exc
        if response.text.strip().startswith("Fails"):
            raise QbittorrentError("qBittorrent 拒绝了该种子文件")

    async def torrents(self, hashes: list[str]) -> list[dict[str, Any]]:
        """按哈希查任务，用于推送后回查是否真的进了列表。"""
        if not hashes:
            return []
        try:
            response = await self.client.get(
                "/api/v2/torrents/info", params={"hashes": "|".join(hashes)}
            )
            response.raise_for_status()
            return list(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise QbittorrentError(f"读取任务列表失败：{exc}") from exc


    async def transfer_info(self) -> dict[str, Any]:
        """全局传输概况：上下行速度与连接状态，用于下载器卡片上的实时展示。"""
        try:
            response = await self.client.get("/api/v2/transfer/info")
            response.raise_for_status()
            return dict(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise QbittorrentError(f"读取下载器状态失败：{exc}") from exc


async def test_connection(payload: schemas.QbittorrentUpdate) -> schemas.QbittorrentTestResultView:
    """按表单值试连。不抛错，把失败原因放进 message 让前端直接展示。"""
    config = schemas.QbittorrentView(
        enabled=True,
        url=payload.url.strip().rstrip("/"),
        username=payload.username.strip(),
        password=payload.password,
    )
    if not config.url:
        return schemas.QbittorrentTestResultView(ok=False, message="请先填写 qBittorrent 地址")
    if not config.url.startswith(("http://", "https://")):
        return schemas.QbittorrentTestResultView(
            ok=False, message="地址需以 http:// 或 https:// 开头"
        )
    try:
        async with QbittorrentClient(config) as client:
            version = await client.version()
            transfer = await client.transfer_info()
    except QbittorrentError as exc:
        return schemas.QbittorrentTestResultView(ok=False, message=str(exc))
    return schemas.QbittorrentTestResultView(
        ok=True,
        message="连接正常",
        version=version,
        dlSpeed=int(transfer.get("dl_info_speed") or 0),
        upSpeed=int(transfer.get("up_info_speed") or 0),
        connectionStatus=str(transfer.get("connection_status") or ""),
    )
