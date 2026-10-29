"""动作服务：转存 / 推送 / 下载（docs/05 §6、docs/07 §2.4）。

动作是异步的：发起即返回 202 + 动作 ID，客户端轮询。
首版把状态放在进程内字典里；接真实源后落 resource_actions 表。

PT 站点的候选只支持 `download`：用站点 Cookie 取到带 passkey 的种子，
直接推给 qBittorrent。这类动作在后台任务里真实执行，状态按执行结果落定。
"""

from __future__ import annotations

import asyncio
import time

from app.api import schemas
from app.errors import ApiError, ErrorCode
from app.providers import site_provider
from app.services import demo_data, preferences, qbittorrent


def _now() -> int:
    """秒级时间戳，契约要求整数（docs/07 §1）。"""
    return int(time.time())

# action_id -> ActionView
_actions: dict[str, schemas.ActionView] = {}

# 真实执行的任务引用，避免被 GC 提前回收
_running: set[asyncio.Task[None]] = set()


def _dir_exists(path: str) -> bool:
    """只支持一层展开 + 面包屑（docs/07 §2.5），这里按演示目录树校验。"""
    parent, _, name = path.rstrip("/").rpartition("/")
    return any(entry.name == name for entry in demo_data.dirs(parent or None).entries)


def _site_candidate(provider_id: str, ref: str) -> schemas.CandidateView | None:
    """站点候选在搜索后不留缓存，按 ref 现算：能拆出站点且站点存在即视为有效。"""
    if not provider_id.startswith("site-"):
        return None
    parsed = site_provider.resolve_ref(ref)
    if parsed is None or f"site-{parsed[0]}" != provider_id:
        return None
    return schemas.CandidateView(
        ref=ref,
        providerId=provider_id,
        providerName=provider_id,
        title=parsed[1],
        actions=[
            schemas.CandidateActionView(
                kind="download", label="推送到 qBittorrent", available=True
            )
        ],
    )


def _require_candidate(provider_id: str, ref: str) -> schemas.CandidateView:
    candidate = demo_data.find_candidate(provider_id, ref) or _site_candidate(provider_id, ref)
    if candidate is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "该候选已失效，请重新搜索")
    return candidate


def _check_available(candidate: schemas.CandidateView, kind: schemas.ActionKind) -> None:
    action = next((a for a in candidate.actions if a.kind == kind), None)
    if action is None or not action.available:
        raise ApiError(
            400,
            ErrorCode.ACTION_NOT_SUPPORTED,
            action.reason if action and action.reason else "该源不支持此操作",
        )


def _require_qbittorrent(user_id: str) -> schemas.QbittorrentView:
    config = preferences.get_qbittorrent(user_id)
    if not config.enabled or not config.url:
        raise ApiError(
            409,
            ErrorCode.QBITTORRENT_NOT_READY,
            "qBittorrent 未启用，请先在「系统 → 设定 → 基础设置」里配置下载器",
        )
    return config


async def _push_to_qbittorrent(
    action_id: str, site_id: int, torrent_id: str, user_id: str, config: schemas.QbittorrentView
) -> None:
    """取种子 → 推给下载器。全过程回写动作状态，失败原因直接给前端展示。"""
    action = _actions.get(action_id)
    if action is None:
        return
    action.status = "running"
    action.updatedAt = _now()
    try:
        url, content = await site_provider.fetch_torrent(site_id, torrent_id, user_id)
        async with qbittorrent.QbittorrentClient(config) as client:
            if content is not None:
                await client.add_file(f"{torrent_id}.torrent", content)
            else:
                await client.add_urls([url])
        action.status = "succeeded"
    except (site_provider.SiteError, qbittorrent.QbittorrentError) as exc:
        action.status = "failed"
        action.failureReason = str(exc) or "推送下载器失败"
    except Exception as exc:  # noqa: BLE001 — 后台任务不能把异常抛给事件循环
        action.status = "failed"
        action.failureReason = f"未预期的错误：{exc}"
    action.updatedAt = _now()


def create(
    provider_id: str, ref: str, kind: schemas.ActionKind, target_dir: str | None, user_id: str
) -> schemas.ActionAcceptedResponse:
    candidate = _require_candidate(provider_id, ref)
    _check_available(candidate, kind)

    site_task: tuple[int, str] | None = None
    qb_config: schemas.QbittorrentView | None = None
    if provider_id.startswith("site-"):
        parsed = site_provider.resolve_ref(ref)
        if parsed is None:
            raise ApiError(404, ErrorCode.NOT_FOUND, "该候选已失效，请重新搜索")
        # 私有站的种子链接带 passkey，必须先确认下载器可用，否则发出去也是白等
        qb_config = _require_qbittorrent(user_id)
        site_task = parsed
    elif kind == "transfer":
        bindings = demo_data.storage_bindings()
        if not any(b.status in ("healthy", "expiring") for b in bindings):
            # 未绑定 → 提示去绑定且**保持登录态**（docs/07 §2.4）
            raise ApiError(409, ErrorCode.STORAGE_AUTH_REQUIRED, "网盘未绑定，请先去管理页绑定")
        if not target_dir:
            target_dir = "/待整理"
        if not _dir_exists(target_dir):
            raise ApiError(400, ErrorCode.INVALID_TARGET_DIR, "目标目录不存在，请重新选择")

    action_id = demo_data.new_id("act")
    now = _now()
    _actions[action_id] = schemas.ActionView(
        id=action_id,
        kind=kind,
        status="pending",
        providerId=provider_id,
        ref=ref,
        title=candidate.title,
        targetDir=target_dir,
        createdAt=now,
        updatedAt=now,
    )
    if site_task is not None and qb_config is not None:
        task = asyncio.create_task(
            _push_to_qbittorrent(action_id, site_task[0], site_task[1], user_id, qb_config)
        )
        _running.add(task)
        task.add_done_callback(_running.discard)
    return schemas.ActionAcceptedResponse(actionId=action_id)


def get(action_id: str) -> schemas.ActionView:
    action = _actions.get(action_id)
    if action is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "动作不存在")
    # 站点动作由后台任务真实执行，状态以它为唯一来源，这里不再推进
    if action.providerId.startswith("site-"):
        return action
    # 演示用：发起后的第一次轮询推进到「执行中」，再下一次成功
    if action.status == "pending":
        action.status = "running"
        action.updatedAt = _now()
    elif action.status == "running":
        action.status = "succeeded"
        action.updatedAt = _now()
        if action.kind == "transfer" and action.itemId is None:
            action.itemId = demo_data.ITEMS[0].id if demo_data.ITEMS else None
    return action


def list_all(cursor: str | None, limit: int) -> schemas.ActionListResponse:
    ordered = sorted(_actions.values(), key=lambda a: a.createdAt, reverse=True)
    start = int(cursor) if cursor and cursor.isdigit() else 0
    page = ordered[start : start + limit]
    next_cursor = str(start + limit) if start + limit < len(ordered) else None
    return schemas.ActionListResponse(actions=page, nextCursor=next_cursor)


def cancel(action_id: str) -> schemas.ActionView:
    action = _actions.get(action_id)
    if action is None:
        raise ApiError(404, ErrorCode.NOT_FOUND, "动作不存在")
    if action.status in ("pending", "running"):
        action.status = "cancelled"
        action.updatedAt = _now()
    return action
