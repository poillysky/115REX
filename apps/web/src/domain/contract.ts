// 契约类型（docs/07）。字段名与后端 JSON 一一对应，禁止在这里做大小写改写。
// 该层不依赖 Vue / 浏览器 API，可单测。

export type ClientPlatform = 'ios' | 'web'
export type BindingStatus = 'healthy' | 'expiring' | 'expired' | 'unbound'
export type ActionKind = 'transfer' | 'push' | 'download'
export type ActionStatus = 'pending' | 'running' | 'succeeded' | 'failed' | 'cancelled'
export type ProviderCapability = 'read_only' | 'direct' | 'transfer' | 'push'
export type ProviderHealth = 'healthy' | 'degraded' | 'circuit_open' | 'half_open' | 'disabled'
export type SourceStatus = 'ok' | 'timeout' | 'error' | 'circuit_open' | 'disabled'

export interface Page {
  nextCursor: string | null
}

// ---- 鉴权

export interface User {
  id: string
  username: string
  displayName: string
  /** 相对路径，如 /api/v1/auth/avatar?u=u-1；未设置头像时为 null */
  avatarUrl?: string | null
}

export interface TokenPair {
  accessToken: string
  refreshToken: string
  expiresIn: number
  tokenType: 'Bearer'
}

export interface LoginResponse extends TokenPair {
  user: User
}

export interface Capabilities {
  search: boolean
  transfer: boolean
  push: boolean
  download: boolean
  play: boolean
  playbackAdapterReady: boolean
}

export interface MeResponse {
  user: User
  server: { version: string; storageProvider: string; mockMode: boolean }
  capabilities: Capabilities
}

// ---- 网盘绑定

/** 网盘容量，字节。totalBytes 为 0 表示 115 没返回，前端据此隐藏容量块。 */
export interface StorageQuota {
  totalBytes: number
  usedBytes: number
}

export interface StorageBinding {
  provider: string
  status: BindingStatus
  displayName: string | null
  /** 115 头像外链；未返回时为 null，前端退回品牌标 */
  avatarUrl?: string | null
  /** 会员等级文案，如「VIP」；无会员时为 null */
  vipLevel?: string | null
  /** 会员到期 Unix 秒；无到期或未返回时为 null */
  vipExpire?: number | null
  updatedAt: number
  /** 账号概况上次从 115 同步的 Unix 秒 */
  syncedAt?: number | null
  quota: StorageQuota | null
}

/** 网盘面包屑节点；根目录 cid 为 \"0\" */
export interface DrivePathNode {
  cid: string
  name: string
}

export interface DriveEntry {
  id: string
  parentId: string
  name: string
  isDir: boolean
  size: number
  modifiedAt: number
  extension: string
  pickCode?: string
  thumbUrl?: string
  previewUrl?: string
}

export interface DriveOpenResult {
  kind: 'image' | 'video' | 'file' | string
  url: string
  name: string
  mimeHint?: string
}

export interface DriveListing {
  cid: string
  count: number
  offset: number
  limit: number
  entries: DriveEntry[]
  path: DrivePathNode[]
}

/** 云下载月度配额 */
export interface OfflineQuota {
  surplus: number
  used: number
  count: number
}

export interface OfflineStatusCounts {
  downloading: number
  failed: number
  finished: number
  total: number
}

/** status: -1 失败 / 0 等待 / 1 下载中 / 2 完成 */
export interface OfflineTask {
  infoHash: string
  name: string
  size: number
  addTime: number
  status: number
  statusText: string
  percentDone: number
  url: string
  fileId: string
  pickCode: string
  wpPathId: string
  fileCategory: number
  rateDownload: number
  leftTime: number
}

export interface OfflineTaskList {
  page: number
  pageCount: number
  count: number
  pageSize: number
  statusCounts: OfflineStatusCounts
  tasks: OfflineTask[]
}

export interface OfflineSummary {
  quota: OfflineQuota
  statusCounts: OfflineStatusCounts
}

export interface OfflineAddResult {
  url: string
  infoHash: string
  name: string
  ok: boolean
  message: string
}

/** 115 扫码会话。qrcode 是二维码**内容**，由前端自行渲染成图。 */
export interface StorageAuthStart {
  sessionId: string
  qrcode: string
  expiresIn: number
  intervalSeconds: number
}

/** 扫码阶段：pending 等待、slow_down 降频、authorized 成功，其余为终止态。 */
export type StorageAuthPollState = 'pending' | 'slow_down' | 'authorized' | 'expired' | 'failed'

export interface StorageAuthPoll {
  state: StorageAuthPollState
  message: string
  retryAfter: number | null
  binding: StorageBinding | null
}

// ---- 搜索（两层：作品 → 候选，客户端不得拍平）

export interface Provider {
  id: string
  name: string
  capability: ProviderCapability
  health: ProviderHealth
  enabled: boolean
  note: string | null
}

export interface CandidateAction {
  kind: ActionKind
  label: string
  available: boolean
  reason: string | null
}

export interface Candidate {
  ref: string
  providerId: string
  providerName: string
  title: string
  sizeBytes: number | null
  resolution: string | null
  sourceType: string | null
  completeness: 'full' | 'partial' | 'unknown'
  seeders: number | null
  actions: CandidateAction[]
}

export interface Work {
  id: string
  title: string
  originalTitle: string | null
  year: number | null
  kind: string
  candidates: Candidate[]
}

export interface SearchSourceStatus {
  providerId: string
  status: SourceStatus
  elapsedMs: number
  candidateCount: number
}

export interface SearchResponse extends Page {
  query: string
  partial: boolean
  sources: SearchSourceStatus[]
  works: Work[]
}

export interface CandidateDetail {
  candidate: Candidate
  description: string | null
  files: string[]
}

// ---- 动作

export interface ActionRecord {
  id: string
  kind: ActionKind
  status: ActionStatus
  providerId: string
  ref: string
  title: string | null
  targetDir: string | null
  progress: number | null
  failureReason: string | null
  itemId: string | null
  createdAt: number
  updatedAt: number
}

// ---- 影视库

export interface SubtitleTrack {
  id: string
  lang: string
  label: string
  format: string
  embedded: boolean
}

export interface AudioTrack {
  id: string
  lang: string
  label: string
  codec: string | null
}

export interface MediaItem {
  id: string
  title: string
  originalTitle: string | null
  year: number | null
  kind: string
  posterUrl: string | null
  durationSeconds: number | null
  sizeBytes: number | null
  resolution: string | null
  favorite: boolean
  progressSeconds: number
  lastPlayedAt: number | null
  sourceProvider: string | null
  sourceRef: string | null
}

export interface MediaItemDetail extends MediaItem {
  overview: string | null
  remotePath: string | null
  audioTracks: AudioTrack[]
  subtitles: SubtitleTrack[]
}

export interface DirEntry {
  name: string
  path: string
  hasChildren: boolean
}

export interface DirsResponse {
  parentPath: string | null
  entries: DirEntry[]
}

export interface PlayInfo {
  url: string
  headers: Record<string, string>
  expiresAt: number
  playToken: string
  startPositionSeconds: number
  subtitles: SubtitleTrack[]
  maxRefresh: number
}

// ---- 偏好

export interface IconLibrary {
  id: string
  name: string
  url: string
  enabled: boolean
}

/** 出站代理。协议由地址的 scheme 表达（http / https / socks5 / socks5h）。 */
export interface NetworkProxy {
  enabled: boolean
  host: string
}

export interface NetworkSettings {
  proxy: NetworkProxy
}

/** 过滤规则档位：off 不过滤、basic 基础去重、strict 严格匹配。 */
export type FilterRule = 'off' | 'basic' | 'strict'

/** 基础设定：访问入口与页面外观。 */
export interface BasicSettings {
  lanUrl: string
  /** 反向代理后的对外地址，如 https://rex.115rex.cn；空表示未配置。 */
  bridgeUrl: string
  filterRule: FilterRule
  doubanCache: boolean
  backgroundImage: string
}

/** GitHub 配置：镜像加速与账号令牌。 */
export interface GithubSettings {
  proxy: string
  token: string
  user: string
}

/** GitHub 授权摘要。服务端只回脱敏值，令牌原文永不下发（docs/07 §2.8.1）。 */
export interface GithubAuthStatus {
  configured: boolean
  /** true 有效、false 已失效、null 暂时无法判断 */
  valid: boolean | null
  /** oauth 设备码授权 / manual 手工令牌 */
  source: 'oauth' | 'manual' | null
  login: string | null
  maskedToken: string | null
  expiresAt: number | null
  needsReauthorization: boolean
  /** 服务端是否配了 OAuth App 的 client_id；未配时只能走手动令牌 */
  clientIdConfigured: boolean
}

/** 设备码授权会话：短码给用户去 GitHub 输入。 */
export interface GithubDeviceAuthStart {
  sessionId: string
  verificationUri: string
  userCode: string
  expiresIn: number
  intervalSeconds: number
}

/** 轮询阶段：pending 等待、slow_down 降频、authorized 成功，其余为终止态。 */
export type GithubAuthPollState =
  | 'pending'
  | 'slow_down'
  | 'authorized'
  | 'denied'
  | 'expired'
  | 'failed'

export interface GithubDeviceAuthPoll {
  state: GithubAuthPollState
  message: string
  retryAfter: number | null
  status: GithubAuthStatus | null
}

/** 高级参数：请求超时（秒）与并发数。 */
export interface AdvancedSettings {
  requestTimeout: number
  concurrency: number
}

/** 插件市场：地址可多个，顺序即查找优先级。 */
export interface PluginSettings {
  market: string[]
  autoReload: boolean
}

/** 插件条目（内置元数据源或市场插件）。 */
export interface PluginItem {
  id: string
  name: string
  author: string
  version: string
  description: string
  kind: string
  capability: string[]
  builtin: boolean
  installed: boolean
  enabled: boolean
  hasUpdate: boolean
  homepage: string
  repoUrl: string
  labels: string[]
  /** 已安装：本地 /api/v1/plugins/{id}/icon；市场预览可为远程 URL */
  iconUrl: string
}

/** 从插件库安装：服务端会把 iconUrl 远程图下载到本地 */
export interface PluginInstall {
  id: string
  name: string
  author?: string
  version?: string
  description?: string
  kind?: string
  capability?: string[]
  homepage?: string
  repoUrl?: string
  labels?: string[]
  iconUrl?: string
}

/** qBittorrent 下载器配置：PT 站点的种子链接统一推给它。 */
export interface QbittorrentSettings {
  enabled: boolean
  /** WebUI 地址，如 http://127.0.0.1:8080 */
  url: string
  username: string
  password: string
  /** 默认分类，留空则用下载器默认分类 */
  category: string
  /** 默认保存路径，留空则用下载器默认路径 */
  savePath: string
}

/** 下载器连通性测试结果。 */
export interface QbittorrentTestResult {
  ok: boolean
  message: string
  version: string
  /** 下载速度，字节/秒 */
  dlSpeed: number | null
  /** 上传速度，字节/秒 */
  upSpeed: number | null
  /** connected / firewalled / disconnected */
  connectionStatus: string
}

/** MoviePilot 接入配置：搜索、识别、整理、加种都交给它，本服务只读状态。 */
export interface MoviepilotSettings {
  enabled: boolean
  /** 后端地址，如 http://192.168.2.38:3000 */
  url: string
  /** API Token，等价超级用户 */
  token: string
}

/** MoviePilot 后台服务的一次执行概况，用于判断自动化流程是否还活着。 */
export interface MoviepilotJob {
  /** 服务标识，如 transfer */
  id: string
  /** 服务名称，如「下载文件整理」 */
  name: string
  /** 服务展示状态，如「等待」「运行中」 */
  status: string
  /** 距下次执行的展示文本，如「3分钟」 */
  nextRun: string
  /** 最近一次执行是否成功；从未执行过时为空 */
  ok: boolean | null
  /** 最近一次执行的错误信息 */
  error: string
  /** 最近一次执行结束时间 */
  finishedAt: string
}

/** MoviePilot 与它名下下载器的运行概况，只供卡片展示。 */
export interface MoviepilotStatus {
  ok: boolean
  message: string
  /** MoviePilot 站点库里启用的站点名 */
  sites: string[]
  /** 默认下载器名称，如 qb */
  downloader: string
  /** 下载器类型，如 qbittorrent */
  downloaderType: string
  /** 下载速度，字节/秒 */
  dlSpeed: number | null
  /** 上传速度，字节/秒 */
  upSpeed: number | null
  /** 下载器累计下载量，字节 */
  dlTotal: number | null
  /** 下载器累计上传量，字节 */
  upTotal: number | null
  /** 下载器所在存储的剩余空间，字节 */
  freeSpace: number | null
  /** 媒体库所在存储的总容量，字节 */
  totalSpace: number | null
  /** 媒体库所在存储的已用容量，字节 */
  usedSpace: number | null
  /** 正在下载的任务数 */
  activeTasks: number
  /** 后台服务里最近一次执行失败或出错的项 */
  jobs: MoviepilotJob[]
  /** MoviePilot 后台服务的总条数 */
  jobTotal: number
  /** connected / firewalled / disconnected */
  connectionStatus: string
}

export interface Preferences {
  defaultTargetDir: string | null
  defaultSubtitleLang: string
  enabledProviders: string[]
  autoTransfer: boolean
  iconLibraries: IconLibrary[]
  /** 40 位十六进制，外部客户端调用控制面时使用 */
  apiToken: string
  network: NetworkSettings
  basic: BasicSettings
  github: GithubSettings
  advanced: AdvancedSettings
  plugins: PluginSettings
  qbittorrent: QbittorrentSettings
  moviepilot: MoviepilotSettings
}

// ---- 站点（MVP，字段语义对齐 MoviePilot Site）

export interface Site {
  id: number
  name: string
  domain: string
  url: string
  pri: number
  rss: string
  cookie: string
  apikey: string
  token: string
  ua: string
  proxy: boolean
  filter: string
  render: boolean
  public: boolean
  note: string
  timeout: number
  downloader: string
  limitInterval: number
  limitCount: number
  limitSeconds: number
  isActive: boolean
}

/** 创建 / 全量更新；不含 id。 */
export type SiteWrite = Omit<Site, 'id'>

export type SitePatch = Partial<Omit<Site, 'id' | 'domain'>>

export interface SiteStatistic {
  domain: string
  success: number
  fail: number
  seconds: number
  /** 0 成功 / 1 失败 */
  lstState: number
  lstModAt: number
  /** 最近一次测试的可读时间 */
  lstModDate: string
  /** 耗时记录 JSON 文本：{"YYYY-MM-DD HH:MM:SS": 秒} */
  note: string
}

export interface SiteTestResult {
  ok: boolean
  seconds: number
  message: string
  statistic: SiteStatistic
}

/** 站点搜索探测的样例种子，下载地址中的 passkey 已打码。 */
export interface SiteProbeSample {
  torrentId: string
  title: string
  subtitle: string
  sizeBytes: number | null
  resolution: string | null
  seeders: number | null
  category: string | null
  snatched: number | null
  promo: string | null
  promoUntil: string | null
  hitAndRun: boolean
  sticky: boolean
  bonus: number | null
  downloadUrl: string
}

/** 站点搜索探测结果：用关键词实抓一次列表页，回报解析情况。 */
export interface SiteProbeResult {
  ok: boolean
  message: string
  seconds: number
  url: string
  matched: number
  samples: SiteProbeSample[]
}

/** 站点站名预取：按站点地址抓首页标题取站名，添加站点时自动填入。 */
export interface SiteMeta {
  name: string
  domain: string
  message: string
}

export type SiteConnectionStatus = 'connected' | 'slow' | 'failed' | 'unknown'

// ---- 元数据发现 / 详情（TMDB / 豆瓣海报墙）

export type MetaSource = 'themoviedb' | 'douban'
export type MetaKind = 'movie' | 'tv'

export interface MetaPerson {
  id: string
  name: string
  character: string
  profileUrl: string | null
}

export interface MetaCard {
  source: MetaSource
  id: string
  kind: MetaKind
  title: string
  originalTitle: string | null
  year: number | null
  posterUrl: string | null
  rating: number | null
  overview: string | null
}

export interface MetaDiscoverResponse {
  source: MetaSource
  kind: MetaKind
  category: string
  page: number
  items: MetaCard[]
  hasMore: boolean
}

export type MetaBoardGroup = 'movie' | 'tv' | 'anime' | 'ranking' | string

export interface MetaBoard {
  id: string
  title: string
  group: MetaBoardGroup
  source: string
  items: MetaCard[]
  message: string
}

export interface MetaBoardsResponse {
  boards: MetaBoard[]
}

export interface MetaDetail {
  source: MetaSource
  id: string
  kind: MetaKind
  title: string
  originalTitle: string | null
  year: number | null
  posterUrl: string | null
  backdropUrl: string | null
  rating: number | null
  overview: string | null
  genres: string[]
  runtimeMinutes: number | null
  cast: MetaPerson[]
  homepage: string | null
}
