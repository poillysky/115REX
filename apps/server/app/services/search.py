"""搜索服务（docs/05 §4–6）。

职责：并发调各源 → 归一化 → 合并成作品 → 排序 → 返回带 partial 的结果。
规矩：单源失败**不**抛 HTTP 错误，只记入源状态；所有源都不可用才抛 PROVIDER_UNAVAILABLE。
"""

from __future__ import annotations

import asyncio
import re
import time

from app.api import schemas
from app.config import get_settings
from app.errors import ApiError, ErrorCode
from app.providers.base import registry
from app.providers.mock import MockQuery
from app.services import demo_data
from app.services.health import health_snapshot

# 真实站点候选没有预置的作品归属，按「清理后的标题 + 年份」自己归组
_YEAR_RE = re.compile(r"[(.．\s_\[【](19\d{2}|20\d{2})[)）\].．\s_\]】]")
_RESOLUTION_RE = re.compile(r"\b(2160p|1440p|1080[pi]|720p|480p)\b", re.I)
_RELEASE_NOISE = re.compile(
    r"\b(BluRay|BDRip|WEB-?DL|WEBRip|HDTV|REMUX|UHD|HDR10?|DV|DoVi|HEVC|H\.?26[45]|x26[45]|"
    r"AAC|DTS(?:-HD)?|TrueHD|Atmos|FLAC|10bit|8bit|Repack|Proper)\b",
    re.I,
)


def _strip_release_group(value: str, original: str) -> str:
    """去掉发布组后缀。原始名里带 `-` 时它会粘成 `Dune Part Two -GRP`，顺手清掉。"""
    if "-" not in original:
        return value
    return re.sub(r"\s*-\s*[A-Za-z0-9@._]+$", "", value).strip()


def _normalize_title(title: str) -> str:
    """把发布名压成可比较的作品名：去季集、分辨率、编码与站点标记。"""
    value = _RESOLUTION_RE.sub(" ", title)
    value = _RELEASE_NOISE.sub(" ", value)
    value = re.sub(r"\[[^\]]*\]|【[^】]*】", " ", value)
    value = re.sub(r"\bS\d{1,2}(E\d{1,3})?\b", " ", value, flags=re.I)
    value = re.sub(r"\bE\d{1,3}\b", " ", value, flags=re.I)
    value = re.sub(r"[._]+", " ", value)
    value = re.sub(r"[()（）\[\]【】]", " ", value)
    value = re.sub(r"(19|20)\d{2}", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" -—|·")
    return _strip_release_group(value, title)


def _candidate_work(candidate: schemas.CandidateView) -> tuple[str, int | None, str]:
    """真实源候选的作品归属：标题 / 年份 / 类型由候选自身推断。"""
    match = _YEAR_RE.search(f" {candidate.title} ")
    year = int(match.group(1)) if match else None
    is_series = bool(
        re.search(r"\bS\d{1,2}(E\d{1,3})?\b", candidate.title, re.I)
        or re.search(r"第[一二三四五六七八九十\d]+季|全\d+集", candidate.title)
    )
    return _normalize_title(candidate.title), year, "series" if is_series else "movie"


def _merge_works(candidates: list[schemas.CandidateView]) -> list[schemas.WorkView]:
    """按「归一化标题 + 年份」合并（docs/05 §4.1）；年份缺失不参与区分。

    演示源的候选有预置作品归属，直接用它；真实源候选（如 PT 站点）没有，
    退回到候选标题推断，否则会被整条丢掉。
    """
    merged: dict[tuple[str, int | None], schemas.WorkView] = {}
    for candidate in candidates:
        work = demo_data.find_work_by_candidate(candidate.ref)
        if work is not None:
            title, year, kind = work.title, work.year, work.kind
            original_title = work.originalTitle
        else:
            title, year, kind = _candidate_work(candidate)
            original_title = None
        if not title:
            continue
        key = (title.strip().lower(), year)
        bucket = merged.get(key)
        if bucket is None:
            merged[key] = schemas.WorkView(
                id=f"w-{len(merged) + 1}",
                title=title,
                originalTitle=original_title,
                year=year,
                kind=kind,
                candidates=[candidate],
            )
        elif not any(c.ref == candidate.ref for c in bucket.candidates):
            bucket.candidates.append(candidate)
    return list(merged.values())


async def search(query: str, providers: list[str] | None) -> schemas.SearchResponse:
    settings = get_settings()

    if settings.mock_mode:
        return demo_data.search(query)

    health = health_snapshot()
    selected = [
        p
        for p in registry.all()
        if p.enabled
        and (providers is None or p.id in providers)
        and health.get(p.id, "healthy") not in ("circuit_open", "disabled")
    ]
    if not selected:
        raise ApiError(503, ErrorCode.PROVIDER_UNAVAILABLE, "所有资源源都不可用，请稍后重试", 30)

    parsed = MockQuery(text=query)
    started = time.perf_counter()

    async def run_one(provider) -> tuple[str, list[schemas.CandidateView] | None, str, int]:
        began = time.perf_counter()
        try:
            # search 内必须有超时保护，源挂起不能拖垮整体搜索（docs/05 §8）
            result = await asyncio.wait_for(
                provider.search(parsed), timeout=settings.search_timeout_seconds
            )
            return provider.id, result, "ok", int((time.perf_counter() - began) * 1000)
        except asyncio.TimeoutError:
            return provider.id, None, "timeout", int((time.perf_counter() - began) * 1000)
        except Exception:  # noqa: BLE001 — 单源异常统一降级，不外抛
            return provider.id, None, "error", int((time.perf_counter() - began) * 1000)

    outcomes = await asyncio.gather(*(run_one(p) for p in selected))

    candidates: list[schemas.CandidateView] = []
    sources: list[schemas.SearchSourceStatus] = []
    for provider_id, result, status, elapsed in outcomes:
        candidates.extend(result or [])
        sources.append(
            schemas.SearchSourceStatus(
                providerId=provider_id,
                status=status,  # type: ignore[arg-type]
                elapsedMs=elapsed,
                candidateCount=len(result or []),
            )
        )

    # 熔断 / 禁用的源也要出现在状态里，否则「源挂了」会被显示成「没搜到」
    for provider in registry.all():
        state = health.get(provider.id, "healthy")
        if provider.id not in {s.providerId for s in sources} and state in (
            "circuit_open",
            "disabled",
        ):
            sources.append(
                schemas.SearchSourceStatus(providerId=provider.id, status=state, elapsedMs=0)
            )

    partial = any(s.status != "ok" for s in sources) or len(selected) < len(registry.enabled())
    _ = time.perf_counter() - started
    return schemas.SearchResponse(
        query=query, partial=partial, sources=sources, works=_merge_works(candidates)
    )
