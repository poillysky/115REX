"""演示资源源。

`REX_MOCK_MODE=1` 时替换真实适配器，让前端能对着两层结构联调。
真实源接入方式见 docs/05 §8：实现 search → 一行注册 → 补归一化规则 → 填能力矩阵。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.api import schemas
from app.services import demo_data


@dataclass(frozen=True)
class MockQuery:
    text: str
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    kind: str | None = None


class MockProvider:
    """从演示数据里筛出自己那一份候选。"""

    def __init__(self, provider_id: str, name: str, capability: schemas.ProviderCapability) -> None:
        self.id = provider_id
        self.name = name
        self.capability = capability
        self.enabled = True

    async def search(self, query: MockQuery) -> list[schemas.CandidateView]:
        keyword = query.text.strip().lower()
        hits: list[schemas.CandidateView] = []
        for work in demo_data.WORKS:
            if keyword and keyword not in work.title.lower() and keyword not in (
                work.originalTitle or ""
            ).lower():
                continue
            hits.extend(c for c in work.candidates if c.providerId == self.id)
        return hits
