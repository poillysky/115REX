"""演示数据（REX_MOCK_MODE=1 时使用）。

真实接入前，让 Web / App 能对着契约联调。数据只在本模块内维护，
services 层通过函数取用，不直接依赖这里的常量。
"""

from __future__ import annotations

import time
import uuid

from app.api import schemas

NOW = int(time.time())
DAY = 24 * 60 * 60


def _ts(days_ago: int) -> int:
    return NOW - days_ago * DAY


PROVIDERS: list[schemas.ProviderView] = [
    schemas.ProviderView(
        id="local-pg", name="自建资源库", capability="transfer", health="healthy", enabled=True
    ),
    schemas.ProviderView(
        id="bitmagnet", name="BitMagnet", capability="direct", health="healthy", enabled=True
    ),
    schemas.ProviderView(
        id="cloudsaver", name="CloudSaver", capability="transfer", health="degraded",
        enabled=True, note="响应偏慢",
    ),
    schemas.ProviderView(
        id="semitio", name="semitio addon", capability="read_only", health="circuit_open",
        enabled=True, note="连续失败已熔断，稍后自动重试",
    ),
]


def providers() -> list[schemas.ProviderView]:
    return PROVIDERS


def provider_ids() -> set[str]:
    return {item.id for item in PROVIDERS}


def storage_bindings() -> list[schemas.StorageBindingView]:
    return [
        schemas.StorageBindingView(
            provider="115",
            status="healthy",
            displayName="主账号",
            expiresAt=NOW + 20 * DAY,
            updatedAt=_ts(3),
        ),
        schemas.StorageBindingView(
            provider="115",
            status="unbound",
            displayName=None,
            expiresAt=None,
            updatedAt=_ts(30),
        ),
    ]


def _actions(transfer_ok: bool = True, direct: bool = False) -> list[schemas.CandidateActionView]:
    return [
        schemas.CandidateActionView(
            kind="transfer",
            label="转存到 115",
            available=transfer_ok,
            reason=None if transfer_ok else "该源不支持转存",
        ),
        schemas.CandidateActionView(
            kind="download",
            label="下载到本地",
            available=direct,
            reason=None if direct else "该源不支持下载",
        ),
    ]


WORKS: list[schemas.WorkView] = [
    schemas.WorkView(
        id="w-arrival",
        title="降临",
        originalTitle="Arrival",
        year=2016,
        kind="movie",
        candidates=[
            schemas.CandidateView(
                ref="c-arrival-4k", providerId="local-pg", providerName="自建资源库",
                title="降临.Arrival.2016.2160p.UHD.BluRay.x265", sizeBytes=19_327_352_832,
                resolution="2160p", sourceType="网盘文件", completeness="full",
                actions=_actions(),
            ),
            schemas.CandidateView(
                ref="c-arrival-1080", providerId="bitmagnet", providerName="BitMagnet",
                title="Arrival.2016.1080p.BluRay.x264", sizeBytes=11_811_160_064,
                resolution="1080p", sourceType="种子", completeness="full", seeders=128,
                actions=_actions(transfer_ok=False, direct=True),
            ),
            schemas.CandidateView(
                ref="c-arrival-web", providerId="cloudsaver", providerName="CloudSaver",
                title="降临 2016 WEB-DL 1080p 国语中字", sizeBytes=4_294_967_296,
                resolution="1080p", sourceType="脚本任务", completeness="full",
                actions=_actions(),
            ),
        ],
    ),
    schemas.WorkView(
        id="w-dune-2",
        title="沙丘 2",
        originalTitle="Dune: Part Two",
        year=2024,
        kind="movie",
        candidates=[
            schemas.CandidateView(
                ref="c-dune2-4k", providerId="local-pg", providerName="自建资源库",
                title="沙丘2.Dune.Part.Two.2024.2160p.WEB-DL.H265", sizeBytes=24_696_061_952,
                resolution="2160p", sourceType="网盘文件", completeness="full",
                actions=_actions(),
            ),
            schemas.CandidateView(
                ref="c-dune2-remux", providerId="bitmagnet", providerName="BitMagnet",
                title="Dune.Part.Two.2024.2160p.REMUX", sizeBytes=64_424_509_440,
                resolution="2160p", sourceType="种子", completeness="full", seeders=42,
                actions=_actions(transfer_ok=False, direct=True),
            ),
        ],
    ),
    schemas.WorkView(
        id="w-severance",
        title="人生切割术",
        originalTitle="Severance",
        year=2022,
        kind="series",
        candidates=[
            schemas.CandidateView(
                ref="c-sev-s1", providerId="local-pg", providerName="自建资源库",
                title="人生切割术.S01.2022.1080p.WEB-DL", sizeBytes=21_474_836_480,
                resolution="1080p", sourceType="网盘文件", completeness="full",
                actions=_actions(),
            ),
            schemas.CandidateView(
                ref="c-sev-s2-part", providerId="cloudsaver", providerName="CloudSaver",
                title="人生切割术 S02 更新至 05 集", sizeBytes=6_442_450_944,
                resolution="1080p", sourceType="脚本任务", completeness="partial",
                actions=_actions(),
            ),
        ],
    ),
    schemas.WorkView(
        id="w-blade-runner",
        title="银翼杀手 2049",
        originalTitle="Blade Runner 2049",
        year=2017,
        kind="movie",
        candidates=[
            schemas.CandidateView(
                ref="c-br2049-1080", providerId="local-pg", providerName="自建资源库",
                title="银翼杀手2049.Blade.Runner.2049.2017.1080p.BluRay", sizeBytes=16_106_127_360,
                resolution="1080p", sourceType="网盘文件", completeness="full",
                actions=_actions(),
            ),
        ],
    ),
]


def search(query: str) -> schemas.SearchResponse:
    """关键词命中标题或原名即算匹配；返回两层结构 + 显式 partial。"""
    keyword = query.strip().lower()
    matched = [
        work
        for work in WORKS
        if not keyword
        or keyword in work.title.lower()
        or (work.originalTitle or "").lower().find(keyword) >= 0
    ] or WORKS

    sources = [
        schemas.SearchSourceStatus(providerId=p.id, status="ok", elapsedMs=120 + index * 90,
                                   candidateCount=sum(
                                       1 for w in matched for c in w.candidates if c.providerId == p.id))
        for index, p in enumerate(PROVIDERS)
        if p.health != "circuit_open"
    ]
    sources.append(
        schemas.SearchSourceStatus(providerId="semitio", status="circuit_open", elapsedMs=0)
    )
    return schemas.SearchResponse(
        query=query,
        partial=True,
        sources=sources,
        works=matched,
        nextCursor=None,
    )


def find_candidate(provider: str, ref: str) -> schemas.CandidateView | None:
    for work in WORKS:
        for candidate in work.candidates:
            if candidate.providerId == provider and candidate.ref == ref:
                return candidate
    return None


def find_work_by_candidate(ref: str) -> schemas.WorkView | None:
    for work in WORKS:
        if any(candidate.ref == ref for candidate in work.candidates):
            return work
    return None


POSTER_BASE = "https://trae-api-cn.mchost.guru/api/ide/v1/tool_text_to_image"


def _poster(prompt: str) -> str:
    from urllib.parse import quote

    return f"{POSTER_BASE}?prompt={quote(prompt)}&image_size=portrait_4_3"


ITEMS: list[schemas.MediaItemDetail] = [
    schemas.MediaItemDetail(
        id="m-001",
        title="降临",
        originalTitle="Arrival",
        year=2016,
        kind="movie",
        overview="语言学家露易丝受政府之邀，破解外星来客的语言，逐渐理解时间并非线性。",
        posterUrl=_poster("cinematic sci-fi movie poster, misty monolith hovering above a field, muted teal and grey tones, minimal typography space"),
        remotePath="/115REX/电影/降临 (2016)/Arrival.2016.2160p.mkv",
        durationSeconds=6960,
        sizeBytes=19_327_352_832,
        resolution="2160p",
        favorite=True,
        progressSeconds=1520,
        lastPlayedAt=_ts(1),
        sourceProvider="local-pg",
        sourceRef="c-arrival-4k",
        audioTracks=[
            schemas.AudioTrackView(id="a1", lang="en", label="英语 5.1", codec="eac3"),
            schemas.AudioTrackView(id="a2", lang="zh-CN", label="国语 2.0", codec="aac"),
        ],
        subtitles=[
            schemas.SubtitleTrackView(id="s1", lang="zh-CN", label="简体中文", format="ass", embedded=True),
            schemas.SubtitleTrackView(id="s2", lang="en", label="English", format="srt", embedded=False),
        ],
    ),
    schemas.MediaItemDetail(
        id="m-002",
        title="沙丘 2",
        originalTitle="Dune: Part Two",
        year=2024,
        kind="movie",
        overview="保罗·厄崔迪与弗雷曼人结盟，向背叛他家族的阴谋者复仇。",
        posterUrl=_poster("epic desert sci-fi movie poster, vast sand dunes, orange and sand tones, lone silhouettes, minimal typography space"),
        remotePath="/115REX/电影/沙丘 2 (2024)/Dune.Part.Two.2024.2160p.mkv",
        durationSeconds=9960,
        sizeBytes=24_696_061_952,
        resolution="2160p",
        favorite=False,
        progressSeconds=0,
        lastPlayedAt=None,
        sourceProvider="local-pg",
        sourceRef="c-dune2-4k",
        audioTracks=[schemas.AudioTrackView(id="a3", lang="en", label="英语 Atmos", codec="truehd")],
        subtitles=[schemas.SubtitleTrackView(id="s3", lang="zh-CN", label="简体中文", format="ass", embedded=True)],
    ),
    schemas.MediaItemDetail(
        id="m-003",
        title="人生切割术",
        originalTitle="Severance",
        year=2022,
        kind="series",
        overview="一家公司用手术把员工的工作记忆与生活记忆彻底分离。",
        posterUrl=_poster("minimal thriller series poster, sterile office corridor, cold blue light, geometric shapes, minimal typography space"),
        remotePath="/115REX/剧集/人生切割术/Season 01/Severance.S01E01.mkv",
        durationSeconds=3420,
        sizeBytes=21_474_836_480,
        resolution="1080p",
        favorite=True,
        progressSeconds=2740,
        lastPlayedAt=_ts(4),
        sourceProvider="local-pg",
        sourceRef="c-sev-s1",
        audioTracks=[schemas.AudioTrackView(id="a4", lang="en", label="英语 5.1", codec="ac3")],
        subtitles=[schemas.SubtitleTrackView(id="s4", lang="zh-CN", label="简体中文", format="srt", embedded=False)],
    ),
    schemas.MediaItemDetail(
        id="m-004",
        title="银翼杀手 2049",
        originalTitle="Blade Runner 2049",
        year=2017,
        kind="movie",
        overview="复制人探员 K 追查一桩旧案，揭开了人与复制人之间的秘密。",
        posterUrl=_poster("neo-noir cyberpunk movie poster, rainy neon city street, magenta and cyan glow, lone figure in coat, minimal typography space"),
        remotePath="/115REX/电影/银翼杀手 2049 (2017)/Blade.Runner.2049.2017.1080p.mkv",
        durationSeconds=9840,
        sizeBytes=16_106_127_360,
        resolution="1080p",
        favorite=False,
        progressSeconds=0,
        lastPlayedAt=None,
        sourceProvider=None,
        sourceRef=None,
        audioTracks=[],
        subtitles=[],
    ),
    schemas.MediaItemDetail(
        id="m-005",
        title="奥本海默",
        originalTitle="Oppenheimer",
        year=2023,
        kind="movie",
        overview="原子弹之父罗伯特·奥本海默的传记故事。",
        posterUrl=_poster("dramatic historical biopic poster, silhouette against a bright explosion light, black and amber tones, minimal typography space"),
        remotePath="/115REX/电影/奥本海默 (2023)/Oppenheimer.2023.2160p.mkv",
        durationSeconds=10800,
        sizeBytes=30_064_771_481,
        resolution="2160p",
        favorite=False,
        progressSeconds=640,
        lastPlayedAt=_ts(9),
        sourceProvider="cloudsaver",
        sourceRef="c-opp-4k",
        audioTracks=[schemas.AudioTrackView(id="a5", lang="en", label="英语 5.1", codec="dts")],
        subtitles=[schemas.SubtitleTrackView(id="s5", lang="zh-CN", label="简体中文", format="ass", embedded=True)],
    ),
    schemas.MediaItemDetail(
        id="m-006",
        title="蜘蛛侠：纵横宇宙",
        originalTitle="Spider-Man: Across the Spider-Verse",
        year=2023,
        kind="movie",
        overview="迈尔斯穿梭多元宇宙，与蜘蛛侠伙伴们一起面对新的威胁。",
        posterUrl=_poster("vibrant animated superhero poster, comic book halftone textures, bold vivid colors, dynamic composition, minimal typography space"),
        remotePath="/115REX/电影/蜘蛛侠 纵横宇宙 (2023)/Across.The.Spider-Verse.2023.2160p.mkv",
        durationSeconds=8400,
        sizeBytes=22_548_578_713,
        resolution="2160p",
        favorite=True,
        progressSeconds=0,
        lastPlayedAt=_ts(15),
        sourceProvider="bitmagnet",
        sourceRef="c-spider-4k",
        audioTracks=[],
        subtitles=[],
    ),
]


def items() -> list[schemas.MediaItemDetail]:
    return ITEMS


def find_item(item_id: str) -> schemas.MediaItemDetail | None:
    return next((item for item in ITEMS if item.id == item_id), None)


def dirs(path: str | None) -> schemas.DirsResponse:
    tree: dict[str, list[str]] = {
        None: ["电影", "剧集", "纪录片", "待整理"],
        "/电影": ["降临 (2016)", "沙丘 2 (2024)", "奥本海默 (2023)"],
        "/剧集": ["人生切割术", "怪奇物语"],
        "/纪录片": ["地球脉动"],
        "/待整理": [],
    }
    current = path or None
    entries = [
        schemas.DirEntryView(
            name=name,
            path=f"{current or ''}/{name}",
            hasChildren=bool(tree.get(f"{current or ''}/{name}")),
        )
        for name in tree.get(current, [])
    ]
    parent = None
    if current:
        parent = current.rsplit("/", 1)[0] or None
    return schemas.DirsResponse(parentPath=parent, entries=entries)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"
