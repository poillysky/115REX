"""资源源适配层（docs/05 §2）。

契约：只有 `search` 必须实现。provider 是普通对象，注册表持有，
不引入框架、不做基类继承、不做生命周期管理。
providers 之间**互不 import**。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.api import schemas


class SearchQuery(Protocol):
    """解析后的查询。字段语义见 docs/05 §3。"""

    text: str
    year: int | None
    season: int | None
    episode: int | None
    kind: str | None


@runtime_checkable
class ResourceProvider(Protocol):
    id: str
    name: str
    capability: schemas.ProviderCapability
    enabled: bool

    async def search(self, query: SearchQuery) -> list[schemas.CandidateView]: ...


class ProviderRegistry:
    """一源一行注册，见 docs/05 §2.3。"""

    def __init__(self) -> None:
        self._providers: dict[str, ResourceProvider] = {}

    def register(self, provider: ResourceProvider) -> None:
        self._providers[provider.id] = provider

    def unregister(self, provider_id: str) -> None:
        """站点增删改后按账号重建，先摘掉旧的再登记新的。"""
        self._providers.pop(provider_id, None)

    def all(self) -> list[ResourceProvider]:
        return list(self._providers.values())

    def enabled(self) -> list[ResourceProvider]:
        return [item for item in self._providers.values() if item.enabled]

    def get(self, provider_id: str) -> ResourceProvider | None:
        return self._providers.get(provider_id)


registry = ProviderRegistry()
