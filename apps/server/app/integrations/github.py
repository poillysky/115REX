"""GitHub OAuth Device Flow 的出站传输（docs/07 §2.8.1）。

只做三件事：申请设备码、用设备码换访问令牌、拿令牌校验身份。
协议细节照 MoviePilot 的实测写法，错误一律收敛成 GithubTransportError，
不把响应原文带进业务错误。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

# 设备码流程申请的权限：读用户信息 + 读写仓库（插件市场与工作流推送需要）
GITHUB_SCOPES = ("read:user", "repo", "workflow")

_DEVICE_CODE_URL = "https://github.com/login/device/code"
_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
_USER_URL = "https://api.github.com/user"

_TIMEOUT_SECONDS = 20


class GithubTransportError(RuntimeError):
    """GitHub 请求失败。unauthorized 为真表示令牌本身已失效（401）。"""

    def __init__(self, message: str, *, unauthorized: bool = False) -> None:
        super().__init__(message)
        self.unauthorized = unauthorized


@dataclass(frozen=True, slots=True)
class DeviceCode:
    device_code: str
    user_code: str
    verification_uri: str
    expires_in: int
    interval_seconds: int


@dataclass(frozen=True, slots=True)
class TokenExchange:
    """设备码换令牌的结果。error 非空时其余字段为空，表示还在等用户或已失败。"""

    access_token: str | None = None
    refresh_token: str | None = None
    expires_in: int | None = None
    refresh_token_expires_in: int | None = None
    scope: str | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class GithubUser:
    login: str
    user_id: int


def _optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class GithubAuthClient:
    """同步 httpx 客户端。授权接口本身是低频动作，不值得引入异步链路。"""

    def __init__(self, proxy: str = "") -> None:
        # 代理来自设置页的 GitHub 加速/出站代理；留空直连
        self._proxy = proxy.strip() or None

    def _request(self, headers: dict[str, str] | None = None) -> httpx.Client:
        request_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "115REX",
        }
        request_headers.update(headers or {})
        # trust_env=False：不让机器上的 HTTP_PROXY 环境变量偷偷改变出口
        return httpx.Client(
            headers=request_headers,
            proxy=self._proxy,
            timeout=_TIMEOUT_SECONDS,
            follow_redirects=True,
            trust_env=False,
        )

    def request_device_code(self, client_id: str) -> DeviceCode:
        """申请设备码。返回短码与用户在 GitHub 上输入的验证地址。"""
        payload = self._post(
            _DEVICE_CODE_URL, {"client_id": client_id, "scope": " ".join(GITHUB_SCOPES)}
        )
        if payload.get("error"):
            raise GithubTransportError("申请 GitHub 设备码失败")
        try:
            return DeviceCode(
                device_code=str(payload["device_code"]),
                user_code=str(payload["user_code"]),
                verification_uri=str(
                    payload.get("verification_uri") or payload.get("verification_url") or ""
                ),
                expires_in=max(int(payload.get("expires_in") or 900), 1),
                interval_seconds=max(int(payload.get("interval") or 5), 1),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise GithubTransportError("GitHub 返回的设备授权信息无效") from exc

    def exchange_device_code(self, client_id: str, device_code: str) -> TokenExchange:
        """轮询一次。等待授权等状态放在 error 字段里，不算传输异常。"""
        payload = self._post(
            _ACCESS_TOKEN_URL,
            {
                "client_id": client_id,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        return self._exchange(payload)

    def refresh_access_token(self, client_id: str, refresh_token: str) -> TokenExchange:
        """用刷新令牌换新的访问令牌。"""
        payload = self._post(
            _ACCESS_TOKEN_URL,
            {
                "client_id": client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        return self._exchange(payload)

    def get_user(self, access_token: str) -> GithubUser:
        """校验令牌并读登录名。401 视为令牌失效，其余错误不判定有效性。"""
        with self._request({"Authorization": f"Bearer {access_token}"}) as client:
            try:
                response = client.get(_USER_URL)
            except httpx.HTTPError as exc:
                raise GithubTransportError("无法连接 GitHub，请稍后重试。") from exc
        if response.status_code == 401:
            raise GithubTransportError("GitHub 令牌已失效", unauthorized=True)
        if response.status_code >= 400:
            raise GithubTransportError("GitHub 令牌校验失败")
        payload = self._json(response)
        login = str(payload.get("login") or "").strip()
        if not login:
            raise GithubTransportError("GitHub 未返回用户信息")
        user_id = payload.get("id")
        if not isinstance(user_id, int) or user_id <= 0:
            raise GithubTransportError("GitHub 未返回有效的用户身份")
        return GithubUser(login=login, user_id=user_id)

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        with self._request() as client:
            try:
                response = client.post(url, json=body)
            except httpx.HTTPError as exc:
                raise GithubTransportError("无法连接 GitHub，请稍后重试。") from exc
        if response.status_code >= 400:
            raise GithubTransportError("GitHub 拒绝了本次请求")
        return self._json(response)

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise GithubTransportError("GitHub 返回了无效响应") from exc
        if not isinstance(payload, dict):
            raise GithubTransportError("GitHub 返回了无效响应")
        return payload

    @classmethod
    def _exchange(cls, payload: dict[str, Any]) -> TokenExchange:
        return TokenExchange(
            access_token=_optional_text(payload.get("access_token")),
            refresh_token=_optional_text(payload.get("refresh_token")),
            expires_in=_optional_int(payload.get("expires_in")),
            refresh_token_expires_in=_optional_int(payload.get("refresh_token_expires_in")),
            scope=_optional_text(payload.get("scope")),
            error=_optional_text(payload.get("error")),
        )
