"""资源源健康与熔断状态（docs/05 §5.3）。

首版只在内存里记状态，进程重启即复位。真实计数在接入真实源时补。
"""

from __future__ import annotations

from app.api import schemas
from app.providers.base import registry

# provider_id -> health；未登记视为 healthy
_health: dict[str, schemas.ProviderHealth] = {}


def health_snapshot() -> dict[str, schemas.ProviderHealth]:
    return {provider.id: _health.get(provider.id, "healthy") for provider in registry.all()}


def provider_views() -> list[schemas.ProviderView]:
    state = health_snapshot()
    return [
        schemas.ProviderView(
            id=provider.id,
            name=provider.name,
            capability=provider.capability,
            health=state.get(provider.id, "healthy"),
            enabled=provider.enabled,
        )
        for provider in registry.all()
    ]
