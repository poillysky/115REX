"""数据实体骨架（docs/06 §3）。

只定实体与关键字段，不定业务逻辑。表结构演进工具见 06 §9 Q6。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # 显示名可改；头像只存本地生成文件的文件名，形如 `avatar-u1.png`
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uq_device"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True)
    platform: Mapped[str] = mapped_column(String(16), default="web")
    app_version: Mapped[str] = mapped_column(String(32), default="dev")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RefreshToken(Base):
    """只存哈希。滚动更新 + 重放检测（docs/06 §7）。"""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_pk: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StorageBinding(Base):
    """115 绑定状态。凭据加密后只在 integrations/115 解密。"""

    __tablename__ = "storage_bindings"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_storage_binding"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32), default="115")
    status: Mapped[str] = mapped_column(String(32), default="unbound")
    credential_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 扫码登录拿到的令牌与刷新元数据。凭据列留作后续加密存储的落点。
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    # Unix 秒；refresh_at + expires_in 小于当前时间即需刷新
    refresh_at: Mapped[int] = mapped_column(Integer, default=0)
    expires_in: Mapped[int] = mapped_column(Integer, default=0)
    # 账号概况缓存：昵称 / 头像 / 会员 / 容量。读失败时保留上次的值
    account_name: Mapped[str] = mapped_column(String(128), default="")
    account_avatar: Mapped[str] = mapped_column(String(512), default="")
    vip_level: Mapped[str] = mapped_column(String(64), default="")
    vip_expire: Mapped[int] = mapped_column(Integer, default=0)
    total_bytes: Mapped[int] = mapped_column(Integer, default=0)
    used_bytes: Mapped[int] = mapped_column(Integer, default=0)
    info_at: Mapped[int] = mapped_column(Integer, default=0)
    # Unix 秒；115 限频（刷新过于频繁）后到这个时间点前不再刷新
    throttle_until: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MediaItem(Base):
    """刮削后的作品条目。幂等键 = 绑定 + 远端路径（docs/06 §5）。"""

    __tablename__ = "media_items"
    __table_args__ = (UniqueConstraint("binding_id", "remote_path", name="uq_media_item"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    binding_id: Mapped[int] = mapped_column(ForeignKey("storage_bindings.id"), index=True)
    remote_path: Mapped[str] = mapped_column(String(1024))
    title: Mapped[str] = mapped_column(String(255))
    original_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str] = mapped_column(String(16), default="movie")
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SubtitleTrack(Base):
    __tablename__ = "subtitle_tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id"), index=True)
    lang: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(64))
    format: Mapped[str] = mapped_column(String(16), default="srt")
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class AudioTrack(Base):
    __tablename__ = "audio_tracks"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("media_items.id"), index=True)
    lang: Mapped[str] = mapped_column(String(16))
    label: Mapped[str] = mapped_column(String(64))
    codec: Mapped[str | None] = mapped_column(String(32), nullable=True)


class ResourceAction(Base):
    """转存等异步动作。进程重启后「执行中」降级为「已中断」。"""

    __tablename__ = "resource_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    ref: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16))  # transfer / push / download
    status: Mapped[str] = mapped_column(String(16), default="pending")
    target_dir: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    progress: Mapped[float | None] = mapped_column(Float, nullable=True)
    item_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Preference(Base):
    """账号级偏好，一个用户一行。嵌套结构（图标库、代理、高级参数）按 JSON 文本存。"""

    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    default_target_dir: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    default_subtitle_lang: Mapped[str] = mapped_column(String(16), default="zh-CN")
    enabled_providers: Mapped[str] = mapped_column(Text, default="[]")
    auto_transfer: Mapped[bool] = mapped_column(Boolean, default=False)
    # 下面两段是 JSON 文本：图标库列表，以及会话里可编辑的基础 / 网络 / GitHub / 高级 / 插件配置
    icon_libraries: Mapped[str] = mapped_column(Text, default="[]")
    settings: Mapped[str] = mapped_column(Text, default="{}")
    api_token: Mapped[str] = mapped_column(String(64), default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Site(Base):
    """资源站点（对齐 MoviePilot 站点字段的精简子集）。账号级，按域名唯一。"""

    __tablename__ = "sites"
    __table_args__ = (UniqueConstraint("user_id", "domain", name="uq_site_domain"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    domain: Mapped[str] = mapped_column(String(255), index=True)
    url: Mapped[str] = mapped_column(String(1024))
    # 数值越小越优先（与 MoviePilot pri 语义一致）
    pri: Mapped[int] = mapped_column(Integer, default=0)
    rss: Mapped[str] = mapped_column(Text, default="")
    cookie: Mapped[str] = mapped_column(Text, default="")
    apikey: Mapped[str] = mapped_column(Text, default="")
    token: Mapped[str] = mapped_column(Text, default="")
    ua: Mapped[str] = mapped_column(Text, default="")
    proxy: Mapped[bool] = mapped_column(Boolean, default=False)
    filter: Mapped[str] = mapped_column(String(255), default="")
    render: Mapped[bool] = mapped_column(Boolean, default=False)
    public: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str] = mapped_column(Text, default="")
    timeout: Mapped[int] = mapped_column(Integer, default=15)
    downloader: Mapped[str] = mapped_column(String(64), default="")
    # 流控（对齐 MoviePilot）：窗口秒数 / 窗口内次数 / 相邻请求最小间隔
    limit_interval: Mapped[int] = mapped_column(Integer, default=0)
    limit_count: Mapped[int] = mapped_column(Integer, default=0)
    limit_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class SiteStatistic(Base):
    """站点连通性统计（对齐 MoviePilot SiteStatistic）。按域名一条。"""

    __tablename__ = "site_statistics"
    __table_args__ = (UniqueConstraint("user_id", "domain", name="uq_site_stat_domain"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    success: Mapped[int] = mapped_column(Integer, default=0)
    fail: Mapped[int] = mapped_column(Integer, default=0)
    # 最近一次耗时（秒，整数）
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    # 0 成功 / 1 失败
    lst_state: Mapped[int] = mapped_column(Integer, default=0)
    lst_mod_at: Mapped[int] = mapped_column(Integer, default=0)
    # 最近一次测试的可读时间，形如 2026-10-27 12:00:00
    lst_mod_date: Mapped[str] = mapped_column(String(32), default="")
    # 耗时记录 JSON 文本：{"2026-10-27 12:00:00": 2}
    note: Mapped[str] = mapped_column(Text, default="")


class GithubAuth(Base):
    """GitHub 授权凭据，一个用户一行（docs/07 §2.8.1）。

    单独成表而不是塞进 Preference：偏好整体回写，凭据混进去会被误清；
    且访问令牌只供服务端出站请求，绝不能进任何接口响应。
    """

    __tablename__ = "github_auth"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    # oauth 为设备码授权，manual 为手工 PAT；空字符串表示未授权
    source: Mapped[str] = mapped_column(String(16), default="")
    access_token: Mapped[str] = mapped_column(Text, default="")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    scope: Mapped[str] = mapped_column(Text, default="")
    login: Mapped[str] = mapped_column(String(64), default="")
    # Unix 秒；0 表示未给出有效期（PAT 不过期）
    expires_at: Mapped[int] = mapped_column(Integer, default=0)
    refresh_expires_at: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
