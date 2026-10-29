"""全部配置走环境变量（见 docs/06 §8）。本地用 .env，不入库。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# app/config.py → app/ → server/
SERVER_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REX_",
        env_file=SERVER_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 必填
    secret_key: str = "dev-only-secret"
    credential_key: str = "dev-only-credential-key"

    # 存储
    database_url: str = f"sqlite:///{(SERVER_ROOT / 'data' / 'rex.db').as_posix()}"

    # 令牌有效期
    access_ttl_seconds: int = 2 * 60 * 60
    refresh_ttl_seconds: int = 30 * 24 * 60 * 60

    # 搜索预算
    search_timeout_seconds: float = 8.0

    # 115 频控（每秒请求数，0 表示不限）
    storage_rate_limit: int = 0

    # 访问 115 时的出口代理（如 http://127.0.0.1:7897）；留空表示直连
    storage_proxy: str = ""

    # 已部署的 MoviePilot 地址与 API_TOKEN。配上之后站点搜索交给它执行，
    # 本服务不再自己解析站点页面；留空则回落到内置解析器。
    moviepilot_url: str = ""
    moviepilot_token: str = ""

    # GitHub OAuth App 的 client_id（设备码流程用）。公开值，不是机密。
    # 默认沿用 MoviePilot 那款已开启 Device Flow 的公开应用，开箱即可授权；
    # 自建 OAuth App 时用 REX_GITHUB_CLIENT_ID 覆盖，置为空串则只保留手动令牌入口。
    github_client_id: str = "Ov23li8tweQw6odWQebz"

    # 115 开放平台的应用 ID（扫码设备码用）。公开值，不是机密。
    # 默认沿用 MoviePilot 那款已开启设备码授权的公开应用，开箱即可扫码。
    u115_app_id: str = "100197847"

    # Web 静态产物目录；为空则用默认的 app/web（npm run build 产物）
    static_dir: str = str(SERVER_ROOT / "app" / "web")

    # 生产由后端同源托管 Web，正常不需要 CORS
    cors_origins: str = ""

    # 未接真实资源源与 115 时返回演示数据
    mock_mode: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
