"""接口层的请求 / 响应模型（docs/07）。

字段级 JSON 以本篇为准：这是客户端唯一能看到的结构。
命名统一用 camelCase，与契约一致，避免客户端做大小写映射。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- 通用

ClientPlatform = Literal["ios", "web"]
BindingStatus = Literal["healthy", "expiring", "expired", "unbound"]
ActionKind = Literal["transfer", "push", "download"]
ActionStatus = Literal["pending", "running", "succeeded", "failed", "cancelled"]
ProviderCapability = Literal["read_only", "direct", "transfer", "push"]
ProviderHealth = Literal["healthy", "degraded", "circuit_open", "half_open", "disabled"]
SourceStatus = Literal["ok", "timeout", "error", "circuit_open", "disabled"]


class Page(BaseModel):
    """分页信封：`nextCursor` 为 null 表示到底（07 §1）。"""

    nextCursor: str | None = None


# ---------------------------------------------------------------- 鉴权


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    displayName: str | None = None


class RegisterStatusResponse(BaseModel):
    """首次进入 Web 时用它决定走注册还是登录。不暴露任何账号信息。"""

    registrationOpen: bool


class UserView(BaseModel):
    id: str
    username: str
    displayName: str
    # 头像下载地址（相对路径）；未设置时为 null，客户端用首字母占位
    avatarUrl: str | None = None


class ProfileUpdateRequest(BaseModel):
    """账号资料。只传要改的字段，null 表示不修改。"""

    displayName: str | None = None
    avatarUrl: str | None = Field(
        default=None, description="data:image/... 形式的图片，服务端裁切后存本地"
    )


class PasswordUpdateRequest(BaseModel):
    currentPassword: str
    newPassword: str


class TokenPair(BaseModel):
    accessToken: str
    refreshToken: str
    expiresIn: int = Field(description="access 剩余有效秒数")
    tokenType: Literal["Bearer"] = "Bearer"


class LoginResponse(TokenPair):
    user: UserView


class RefreshRequest(BaseModel):
    refreshToken: str


class RefreshResponse(TokenPair):
    pass


class ServerInfo(BaseModel):
    version: str
    storageProvider: str = "115"
    mockMode: bool


class CapabilityView(BaseModel):
    """按能力开关功能，不靠版本号（07 §2.1）。"""

    search: bool = True
    transfer: bool = True
    push: bool = False
    download: bool = False
    play: bool = False
    playbackAdapterReady: bool = False


class MeResponse(BaseModel):
    user: UserView
    server: ServerInfo
    capabilities: CapabilityView


# ---------------------------------------------------------------- 网盘绑定


class StorageQuotaView(BaseModel):
    """网盘容量，字节。0 表示 115 未返回该字段，前端据此隐藏进度条。"""

    totalBytes: int = 0
    usedBytes: int = 0


class StorageBindingView(BaseModel):
    """只读状态，**不含任何凭据**（07 §2.2、§4 第 6 条）。

    不下发令牌到期时间：访问令牌由服务端自动续期，授权没有固定到期日。
    syncedAt 是账号概况（昵称 / 容量 / 会员）上次从 115 拉回的时间。
    """

    provider: str
    status: BindingStatus
    displayName: str | None = None
    avatarUrl: str | None = None
    vipLevel: str | None = None
    vipExpire: int | None = None
    updatedAt: int
    syncedAt: int | None = None
    quota: StorageQuotaView | None = None


class StorageBindingsResponse(BaseModel):
    bindings: list[StorageBindingView]


class P115AuthStartView(BaseModel):
    """扫码登录会话。qrcode 是二维码**内容**，由前端自行渲染成图。"""

    sessionId: str
    qrcode: str
    expiresIn: int
    intervalSeconds: int


class P115AuthPollView(BaseModel):
    """state 取 pending / slow_down / authorized / expired / failed。"""

    state: str
    message: str = ""
    retryAfter: int | None = None
    binding: StorageBindingView | None = None


class P115AuthPollRequest(BaseModel):
    sessionId: str


class DrivePathNodeView(BaseModel):
    cid: str
    name: str


class DriveEntryView(BaseModel):
    id: str
    parentId: str
    name: str
    isDir: bool
    size: int = 0
    modifiedAt: int = 0
    extension: str = ""
    pickCode: str = ""
    thumbUrl: str = ""
    previewUrl: str = ""


class DriveListingView(BaseModel):
    cid: str
    count: int
    offset: int
    limit: int
    entries: list[DriveEntryView]
    path: list[DrivePathNodeView]


class DriveMkdirRequest(BaseModel):
    parentId: str = "0"
    name: str


class DriveRenameRequest(BaseModel):
    fileId: str
    name: str


class DriveDeleteRequest(BaseModel):
    fileIds: list[str]


class DriveOpenRequest(BaseModel):
    pickCode: str
    extension: str = ""
    name: str = ""


class DriveOpenView(BaseModel):
    kind: str
    url: str
    name: str
    mimeHint: str = ""


class OfflineQuotaView(BaseModel):
    surplus: int
    used: int
    count: int


class OfflineStatusCountsView(BaseModel):
    downloading: int = 0
    failed: int = 0
    finished: int = 0
    total: int = 0


class OfflineTaskView(BaseModel):
    infoHash: str
    name: str
    size: int = 0
    addTime: int = 0
    status: int
    statusText: str = ""
    percentDone: float = 0
    url: str = ""
    fileId: str = ""
    pickCode: str = ""
    wpPathId: str = ""
    fileCategory: int = 0
    rateDownload: int = 0
    leftTime: int = 0


class OfflineTaskListView(BaseModel):
    page: int
    pageCount: int
    count: int
    pageSize: int
    statusCounts: OfflineStatusCountsView
    tasks: list[OfflineTaskView]


class OfflineSummaryView(BaseModel):
    quota: OfflineQuotaView
    statusCounts: OfflineStatusCountsView


class OfflineAddRequest(BaseModel):
    urls: list[str]
    wpPathId: str = "0"


class OfflineAddResultView(BaseModel):
    url: str
    infoHash: str = ""
    name: str = ""
    ok: bool = True
    message: str = ""


class OfflineAddResponse(BaseModel):
    results: list[OfflineAddResultView]


class OfflineDeleteRequest(BaseModel):
    infoHash: str
    delSourceFile: bool = False


# ---------------------------------------------------------------- 搜索


class ProviderView(BaseModel):
    id: str
    name: str
    capability: ProviderCapability
    health: ProviderHealth
    enabled: bool
    note: str | None = None


class ProvidersResponse(BaseModel):
    providers: list[ProviderView]


class CandidateActionView(BaseModel):
    """候选当前可执行的动作。客户端据此决定按钮显隐（07 §2.3）。"""

    kind: ActionKind
    label: str
    available: bool
    reason: str | None = Field(default=None, description="不可用时的可读原因")


class CandidateView(BaseModel):
    ref: str
    providerId: str
    providerName: str
    title: str
    sizeBytes: int | None = None
    resolution: str | None = None
    sourceType: str | None = None
    completeness: Literal["full", "partial", "unknown"] = "unknown"
    seeders: int | None = Field(default=None, description="仅同源可比，禁止跨源热度加权")
    actions: list[CandidateActionView] = Field(default_factory=list)


class WorkView(BaseModel):
    """作品层。候选嵌在作品里，客户端不得拍平（08 §5 不变量 3）。"""

    id: str
    title: str
    originalTitle: str | None = None
    year: int | None = None
    kind: str = "movie"
    candidates: list[CandidateView] = Field(default_factory=list)


class SearchSourceStatus(BaseModel):
    providerId: str
    status: SourceStatus
    elapsedMs: int
    candidateCount: int = 0


class SearchResponse(Page):
    query: str
    partial: bool = Field(description="任一源未成功返回即为真，客户端必须提示")
    sources: list[SearchSourceStatus] = Field(default_factory=list)
    works: list[WorkView] = Field(default_factory=list)


class CandidateDetailResponse(BaseModel):
    candidate: CandidateView
    description: str | None = None
    files: list[str] = Field(default_factory=list, description="源侧文件列表，未知时为空")


# ---------------------------------------------------------------- 动作


class ActionRequest(BaseModel):
    kind: ActionKind
    targetDir: str | None = None


class ActionView(BaseModel):
    id: str
    kind: ActionKind
    status: ActionStatus
    providerId: str
    ref: str
    title: str | None = None
    targetDir: str | None = None
    progress: float | None = Field(default=None, description="源侧不提供就为 null，不给假进度")
    failureReason: str | None = None
    itemId: str | None = None
    createdAt: int
    updatedAt: int


class ActionAcceptedResponse(BaseModel):
    actionId: str
    status: ActionStatus = "pending"


class ActionListResponse(Page):
    actions: list[ActionView] = Field(default_factory=list)


# ---------------------------------------------------------------- 影视库


class SubtitleTrackView(BaseModel):
    id: str
    lang: str
    label: str
    format: str
    embedded: bool


class AudioTrackView(BaseModel):
    id: str
    lang: str
    label: str
    codec: str | None = None


class MediaItemView(BaseModel):
    """列表项。**不含播放地址**（07 §2.5）。"""

    id: str
    title: str
    originalTitle: str | None = None
    year: int | None = None
    kind: str = "movie"
    posterUrl: str | None = None
    durationSeconds: int | None = None
    sizeBytes: int | None = None
    resolution: str | None = None
    favorite: bool = False
    progressSeconds: int = 0
    lastPlayedAt: int | None = None
    sourceProvider: str | None = None
    sourceRef: str | None = None


class MediaItemListResponse(Page):
    items: list[MediaItemView] = Field(default_factory=list)


class MediaItemDetail(MediaItemView):
    overview: str | None = None
    remotePath: str | None = None
    audioTracks: list[AudioTrackView] = Field(default_factory=list)
    subtitles: list[SubtitleTrackView] = Field(default_factory=list)


class DirEntryView(BaseModel):
    name: str
    path: str
    hasChildren: bool = False


class DirsResponse(BaseModel):
    parentPath: str | None = Field(default=None, description="路径面包屑上一级，根为 null")
    entries: list[DirEntryView] = Field(default_factory=list)


class ContinueResponse(BaseModel):
    items: list[MediaItemView] = Field(default_factory=list)


class PlayInfoResponse(BaseModel):
    """契约禁止项：不得出现 115 Cookie、refresh token、永久直链（07 §2.6）。"""

    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    expiresAt: int
    playToken: str
    startPositionSeconds: int = 0
    subtitles: list[SubtitleTrackView] = Field(default_factory=list)
    maxRefresh: int = 10


class ProgressRequest(BaseModel):
    positionSeconds: int
    clientTimestamp: int = Field(description="客户端时间戳，服务端取较新者，避免多端覆盖")


class ProgressResponse(BaseModel):
    progressSeconds: int
    lastPlayedAt: int


class FavoriteRequest(BaseModel):
    favorite: bool


class FavoriteResponse(BaseModel):
    favorite: bool


# ---------------------------------------------------------------- 偏好


class IconLibraryView(BaseModel):
    id: str
    name: str
    url: str
    enabled: bool


class IconLibraryUpdate(BaseModel):
    """增删改图标库。id 缺省表示新增，由服务端生成。"""

    id: str | None = None
    name: str
    url: str
    enabled: bool = True


class IconLibrariesUpdate(BaseModel):
    """整表替换；顺序即生效优先级。"""

    libraries: list[IconLibraryUpdate]


class IconLibraryEntryView(BaseModel):
    """图标库里的一个条目：名称 + 可直接使用的图片地址。"""

    name: str
    url: str


class ProxyView(BaseModel):
    """出站代理。协议由地址的 scheme 表达（http / https / socks5 / socks5h）。"""

    enabled: bool = False
    host: str = "http://127.0.0.1:7897"


class NetworkView(BaseModel):
    proxy: ProxyView = Field(default_factory=ProxyView)


class ProxyUpdate(BaseModel):
    """整段提交，避免逐字段合并产生半有效状态。"""

    enabled: bool
    host: str


class NetworkUpdate(BaseModel):
    proxy: ProxyUpdate


class BasicView(BaseModel):
    """基础设定：页面外观与访问入口。"""

    lanUrl: str = ""
    bridgeUrl: str = ""
    filterRule: str = "basic"
    doubanCache: bool = True
    backgroundImage: str = ""


class GithubView(BaseModel):
    """GitHub 配置：镜像加速与账号令牌。"""

    proxy: str = ""
    token: str = ""
    user: str = ""


class AdvancedView(BaseModel):
    """高级参数：请求超时与并发。"""

    requestTimeout: int = 15
    concurrency: int = 8


class MoviepilotView(BaseModel):
    """MoviePilot 接入配置：自动化流程（搜索、识别、整理、加种）全部交给它。

    本服务只读它的状态用于展示，不改它的流程，因此这里只需要地址与令牌。
    """

    enabled: bool = False
    url: str = ""
    token: str = ""


class MoviepilotUpdate(BaseModel):
    """整段提交，避免逐字段合并产生半有效状态。"""

    enabled: bool
    url: str
    token: str


class MoviepilotJobView(BaseModel):
    """MoviePilot 后台服务的一次执行概况，用于判断自动化流程是否还活着。"""

    id: str = Field(default="", description="服务标识，如 transfer")
    name: str = Field(default="", description="服务名称，如「下载文件整理」")
    status: str = Field(default="", description="服务展示状态，如「等待」「运行中」")
    nextRun: str = Field(default="", description="距下次执行的展示文本，如「3分钟」")
    ok: bool | None = Field(default=None, description="最近一次执行是否成功；从未执行过时为空")
    error: str = Field(default="", description="最近一次执行的错误信息")
    finishedAt: str = Field(default="", description="最近一次执行结束时间")


class MoviepilotStatusView(BaseModel):
    """MoviePilot 与它名下下载器的运行概况，只供卡片展示。"""

    ok: bool
    message: str = ""
    # 站点清单与下载器清单只取名字，用来确认两边站点是否对得上
    sites: list[str] = Field(default_factory=list)
    downloader: str = Field(default="", description="默认下载器名称，如 qb")
    downloaderType: str = Field(default="", description="下载器类型，如 qbittorrent")
    dlSpeed: int | None = Field(default=None, description="下载速度，字节/秒")
    upSpeed: int | None = Field(default=None, description="上传速度，字节/秒")
    dlTotal: int | None = Field(default=None, description="下载器累计下载量，字节")
    upTotal: int | None = Field(default=None, description="下载器累计上传量，字节")
    freeSpace: int | None = Field(default=None, description="下载器所在存储的剩余空间，字节")
    totalSpace: int | None = Field(default=None, description="媒体库所在存储的总容量，字节")
    usedSpace: int | None = Field(default=None, description="媒体库所在存储的已用容量，字节")
    activeTasks: int = Field(default=0, description="正在下载的任务数")
    jobs: list[MoviepilotJobView] = Field(
        default_factory=list, description="后台服务里最近一次执行失败或出错的项"
    )
    jobTotal: int = Field(default=0, description="MoviePilot 后台服务的总条数")
    connectionStatus: str = Field(default="", description="connected / firewalled / disconnected")


class QbittorrentView(BaseModel):
    """qBittorrent 下载器配置：WebUI 地址、账号与默认分类/保存路径。

    PT 站点下载统一走 qBittorrent：搜索结果的种子链接带个人 passkey，
    直接推给下载器才会计入分享率，因此这里不经过 115 转存。
    """

    enabled: bool = False
    url: str = ""
    username: str = ""
    password: str = ""
    category: str = ""
    savePath: str = ""


class QbittorrentUpdate(BaseModel):
    """整段提交，避免逐字段合并产生半有效状态。"""

    enabled: bool
    url: str
    username: str
    password: str
    category: str = ""
    savePath: str = ""


class QbittorrentTestResultView(BaseModel):
    """下载器连通性测试结果。"""

    ok: bool
    message: str = ""
    version: str = ""
    # 试连成功时顺带带回传输概况，下载器卡片不用再发一次请求
    dlSpeed: int | None = Field(default=None, description="下载速度，字节/秒")
    upSpeed: int | None = Field(default=None, description="上传速度，字节/秒")
    connectionStatus: str = Field(default="", description="connected / firewalled / disconnected")


class TokenView(BaseModel):
    """API 令牌：40 位十六进制，供外部客户端调用控制面。"""

    apiToken: str = ""


class TokenUpdate(BaseModel):
    apiToken: str


class BasicUpdate(BaseModel):
    lanUrl: str = ""
    bridgeUrl: str = ""
    filterRule: str = "basic"
    doubanCache: bool = True
    backgroundImage: str = ""


class GithubUpdate(BaseModel):
    proxy: str = ""
    token: str = ""
    user: str = ""


class GithubAuthStatusView(BaseModel):
    """GitHub 授权摘要。永远不含令牌原文与刷新令牌（docs/07 §2.8.1）。"""

    configured: bool = False
    # True 有效、False 已失效、None 暂时无法判断（如网络不可达）
    valid: bool | None = None
    # oauth 设备码授权 / manual 手工令牌
    source: str | None = None
    login: str | None = None
    maskedToken: str | None = None
    expiresAt: int | None = None
    needsReauthorization: bool = False
    clientIdConfigured: bool = False


class GithubDeviceAuthStartView(BaseModel):
    sessionId: str
    verificationUri: str
    userCode: str
    expiresIn: int
    intervalSeconds: int


class GithubDeviceAuthPollView(BaseModel):
    """state 取 pending / slow_down / authorized / denied / expired / failed。"""

    state: str
    message: str = ""
    retryAfter: int | None = None
    status: GithubAuthStatusView | None = None


class GithubDeviceAuthPollRequest(BaseModel):
    sessionId: str


class GithubManualTokenRequest(BaseModel):
    token: str


class AdvancedUpdate(BaseModel):
    requestTimeout: int
    concurrency: int


class PluginView(BaseModel):
    """插件市场。地址可多个，逗号或换行分隔。"""

    market: list[str] = Field(default_factory=list)
    autoReload: bool = False


class PluginUpdate(BaseModel):
    market: list[str] = Field(default_factory=list)
    autoReload: bool


class PluginItemView(BaseModel):
    """插件条目：内置元数据源或市场插件。"""

    id: str
    name: str
    author: str = ""
    version: str = "1.0.0"
    description: str = ""
    kind: str = "mediarecognize"
    capability: list[str] = Field(default_factory=list)
    builtin: bool = False
    installed: bool = False
    enabled: bool = False
    hasUpdate: bool = False
    homepage: str = ""
    repoUrl: str = ""
    labels: list[str] = Field(default_factory=list)
    iconUrl: str = Field(
        default="",
        description="已安装为本地 /api/v1/plugins/{id}/icon；市场预览可为远程 URL",
    )


class PluginListView(BaseModel):
    plugins: list[PluginItemView] = Field(default_factory=list)


class PluginPatch(BaseModel):
    enabled: bool | None = None


class PluginInstall(BaseModel):
    """从插件库安装：元数据入库，并把 iconUrl 指向的远程图下载到本地。"""

    id: str
    name: str
    author: str = ""
    version: str = "1.0.0"
    description: str = ""
    kind: str = "mediarecognize"
    capability: list[str] = Field(default_factory=list)
    homepage: str = ""
    repoUrl: str = ""
    labels: list[str] = Field(default_factory=list)
    iconUrl: str = Field(default="", description="安装时下载的远程图标地址，可空")


class PluginConfigView(BaseModel):
    """插件可配置项：启停 + 密钥等（按插件 id 扩展字段）。"""

    enabled: bool = True
    apiKey: str = ""


class PluginConfigUpdate(BaseModel):
    enabled: bool | None = None
    apiKey: str | None = None


class PreferencesView(BaseModel):
    defaultTargetDir: str | None = None
    defaultSubtitleLang: str = "zh-CN"
    enabledProviders: list[str] = Field(default_factory=list)
    autoTransfer: bool = False
    iconLibraries: list[IconLibraryView] = Field(default_factory=list)
    apiToken: str = ""
    network: NetworkView = Field(default_factory=NetworkView)
    basic: BasicView = Field(default_factory=BasicView)
    github: GithubView = Field(default_factory=GithubView)
    advanced: AdvancedView = Field(default_factory=AdvancedView)
    plugins: PluginView = Field(default_factory=PluginView)
    qbittorrent: QbittorrentView = Field(default_factory=QbittorrentView)
    moviepilot: MoviepilotView = Field(default_factory=MoviepilotView)


class PreferencesUpdate(BaseModel):
    defaultTargetDir: str | None = None
    defaultSubtitleLang: str | None = None
    enabledProviders: list[str] | None = None
    autoTransfer: bool | None = None


# ---------------------------------------------------------------- 站点（MVP：列表 / 增删改 / JSON 导入）


class SiteView(BaseModel):
    """站点配置。字段语义对齐 MoviePilot Site，命名走 camelCase。"""

    id: int
    name: str
    domain: str
    url: str
    pri: int = 0
    rss: str = ""
    cookie: str = ""
    apikey: str = ""
    token: str = ""
    ua: str = ""
    proxy: bool = False
    filter: str = ""
    render: bool = False
    public: bool = False
    note: str = ""
    timeout: int = 15
    downloader: str = ""
    limitInterval: int = 0
    limitCount: int = 0
    limitSeconds: int = 0
    isActive: bool = True


class SiteWrite(BaseModel):
    """创建 / 更新共用体。domain 创建后不可改，更新时忽略。"""

    name: str
    domain: str
    url: str
    pri: int = 0
    rss: str = ""
    cookie: str = ""
    apikey: str = ""
    token: str = ""
    ua: str = ""
    proxy: bool = False
    filter: str = ""
    render: bool = False
    public: bool = False
    note: str = ""
    timeout: int = 15
    downloader: str = ""
    limitInterval: int = 0
    limitCount: int = 0
    limitSeconds: int = 0
    isActive: bool = True


class SitePatch(BaseModel):
    """局部更新：只传要改的字段。"""

    name: str | None = None
    url: str | None = None
    pri: int | None = None
    rss: str | None = None
    cookie: str | None = None
    apikey: str | None = None
    token: str | None = None
    ua: str | None = None
    proxy: bool | None = None
    filter: str | None = None
    render: bool | None = None
    public: bool | None = None
    note: str | None = None
    timeout: int | None = None
    downloader: str | None = None
    limitInterval: int | None = None
    limitCount: int | None = None
    limitSeconds: int | None = None
    isActive: bool | None = None


class SiteListView(BaseModel):
    sites: list[SiteView] = Field(default_factory=list)


class SiteStatisticView(BaseModel):
    domain: str
    success: int = 0
    fail: int = 0
    seconds: int = 0
    # 0 成功 / 1 失败；未测过时前端按 unknown 处理
    lstState: int = 0
    lstModAt: int = 0
    # 最近一次测试的可读时间
    lstModDate: str = ""
    # 耗时记录 JSON 文本：{"YYYY-MM-DD HH:MM:SS": 秒}
    note: str = ""


class SiteStatisticListView(BaseModel):
    stats: list[SiteStatisticView] = Field(default_factory=list)


class SiteTestResultView(BaseModel):
    ok: bool
    seconds: float
    message: str = ""
    statistic: SiteStatisticView


class SiteProbeSampleView(BaseModel):
    """探测命中的一条种子，只给前端看解析结果是否对得上。"""

    torrentId: str = Field(default="", description="站点内的种子 ID，详情页与下载页都用它")
    title: str
    subtitle: str = Field(default="", description="标题下方的中文译名，站点不提供时为空")
    sizeBytes: int | None = None
    resolution: str | None = None
    seeders: int | None = None
    category: str | None = Field(default=None, description="分类地址，NexusPHP 为 torrents.php?cat=N")
    snatched: int | None = Field(default=None, description="完成下载次数")
    promo: str | None = Field(default=None, description="促销类型，如「2X 免费」，无促销为空")
    promoUntil: str | None = Field(default=None, description="促销到期时间，站点未提供为空")
    hitAndRun: bool = Field(default=False, description="是否带 H&R 考核")
    sticky: bool = Field(default=False, description="是否置顶")
    bonus: int | None = Field(default=None, description="促销附带的奖励魔力")
    downloadUrl: str = Field(default="", description="补全后的下载地址，含 passkey 时已脱敏")


class SiteProbeResultView(BaseModel):
    """站点搜索探测：用关键词真实抓一次列表页，回报解析情况。"""

    ok: bool
    message: str = ""
    seconds: float = 0
    url: str = ""
    matched: int = 0
    samples: list[SiteProbeSampleView] = Field(default_factory=list)


class SiteMetaView(BaseModel):
    """按站点地址预取站名，前端添加站点时自动填入，无需用户手填。"""

    name: str = ""
    domain: str = ""
    message: str = ""


class SitePriorityItem(BaseModel):
    id: int
    pri: int


class SitePriorityUpdate(BaseModel):
    items: list[SitePriorityItem] = Field(default_factory=list)


# ---- 元数据发现 / 详情（TMDB / 豆瓣出海报墙）


class MetaPersonView(BaseModel):
    id: str = ""
    name: str
    character: str = ""
    profileUrl: str | None = None


class MetaCardView(BaseModel):
    """海报墙卡片：列表字段够点进详情即可。"""

    source: str
    id: str
    kind: str
    title: str
    originalTitle: str | None = None
    year: int | None = None
    posterUrl: str | None = None
    rating: float | None = None
    overview: str | None = None


class MetaDiscoverResponse(BaseModel):
    source: str
    kind: str
    category: str = "trending"
    page: int = 1
    items: list[MetaCardView] = Field(default_factory=list)
    hasMore: bool = False


class MetaBoardView(BaseModel):
    """推荐首页一条横滑榜单。group: movie / tv / anime / ranking。"""

    id: str
    title: str
    group: str = "ranking"
    source: str = ""
    items: list[MetaCardView] = Field(default_factory=list)
    message: str = ""


class MetaBoardsResponse(BaseModel):
    boards: list[MetaBoardView] = Field(default_factory=list)


class MetaDetailView(BaseModel):
    """纯元数据详情：海报 / 简介 / 类型 / 演职员，不含播放。"""

    source: str
    id: str
    kind: str
    title: str
    originalTitle: str | None = None
    year: int | None = None
    posterUrl: str | None = None
    backdropUrl: str | None = None
    rating: float | None = None
    overview: str | None = None
    genres: list[str] = Field(default_factory=list)
    runtimeMinutes: int | None = None
    cast: list[MetaPersonView] = Field(default_factory=list)
    homepage: str | None = None
