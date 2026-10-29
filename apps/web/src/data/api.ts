// 契约调用的唯一出口（docs/07）。application 层只调这里，不直接 fetch。

import { http, request } from '@/core/api/client'
import type {
  ActionRecord,
  AdvancedSettings,
  BasicSettings,
  CandidateDetail,
  DirsResponse,
  GithubAuthStatus,
  GithubDeviceAuthPoll,
  GithubDeviceAuthStart,
  GithubSettings,
  IconLibrary,
  LoginResponse,
  MediaItem,
  MediaItemDetail,
  MeResponse,
  MetaBoardsResponse,
  MetaDetail,
  MetaDiscoverResponse,
  MetaKind,
  MetaSource,
  NetworkProxy,
  Page,
  PlayInfo,
  PluginInstall,
  PluginItem,
  PluginSettings,
  MoviepilotSettings,
  MoviepilotStatus,
  Preferences,
  Provider,
  QbittorrentSettings,
  QbittorrentTestResult,
  SearchResponse,
  StorageAuthPoll,
  StorageAuthStart,
  DriveEntry,
  DriveListing,
  DriveOpenResult,
  OfflineAddResult,
  OfflineQuota,
  OfflineSummary,
  OfflineTaskList,
  Site,
  SitePatch,
  SiteProbeResult,
  SiteMeta,
  SiteStatistic,
  SiteTestResult,
  SiteWrite,
  StorageBinding,
  TokenPair,
  User,
} from '@/domain/contract'

export const authApi = {
  registrationStatus: () =>
    request<{ registrationOpen: boolean }>('/auth/registration', { anonymous: true }),
  register: (username: string, password: string) =>
    request<LoginResponse>('/auth/register', {
      method: 'POST',
      body: { username, password },
      anonymous: true,
    }),
  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: { username, password },
      anonymous: true,
    }),
  me: () => http.get<MeResponse>('/auth/me'),
  updateProfile: (patch: { displayName?: string; avatarUrl?: string }) =>
    http.patch<User>('/auth/profile', patch),
  changePassword: (currentPassword: string, newPassword: string) =>
    http.put<void>('/auth/password', { currentPassword, newPassword }),
  logout: () => http.post<void>('/auth/logout'),
}

export const storageApi = {
  bindings: () => http.get<{ bindings: StorageBinding[] }>('/storage/bindings'),
  startAuth: () => http.post<StorageAuthStart>('/storage/115/auth/start'),
  pollAuth: (sessionId: string) =>
    http.post<StorageAuthPoll>('/storage/115/auth/poll', { sessionId }),
  unbind: () => http.post<{ bindings: StorageBinding[] }>('/storage/115/auth/unbind'),
  listFiles: (params: {
    cid?: string
    offset?: number
    limit?: number
    order?: string
    asc?: boolean
  }) =>
    http.get<DriveListing>('/storage/115/files', {
      cid: params.cid ?? '0',
      offset: params.offset ?? 0,
      limit: params.limit ?? 200,
      order: params.order ?? 'user_utime',
      asc: params.asc ? 'true' : 'false',
    }),
  mkdir: (parentId: string, name: string) =>
    http.post<DriveEntry>('/storage/115/files/mkdir', { parentId, name }),
  rename: (fileId: string, name: string) =>
    http.post<void>('/storage/115/files/rename', { fileId, name }),
  deleteFiles: (fileIds: string[]) =>
    http.post<void>('/storage/115/files/delete', { fileIds }),
  openFile: (payload: { pickCode: string; extension?: string; name?: string }) =>
    http.post<DriveOpenResult>('/storage/115/files/open', payload),
  offlineQuota: () => http.get<OfflineQuota>('/storage/115/offline/quota'),
  offlineSummary: () => http.get<OfflineSummary>('/storage/115/offline/summary'),
  offlineTasks: (params: { page?: number; pageSize?: number; status?: string } = {}) =>
    http.get<OfflineTaskList>('/storage/115/offline/tasks', {
      page: params.page ?? 1,
      pageSize: params.pageSize ?? 30,
      status: params.status,
    }),
  offlineAdd: (urls: string[], wpPathId = '0') =>
    http.post<{ results: OfflineAddResult[] }>('/storage/115/offline/tasks', {
      urls,
      wpPathId,
    }),
  offlineDelete: (infoHash: string, delSourceFile = false) =>
    http.post<void>('/storage/115/offline/tasks/delete', { infoHash, delSourceFile }),
}

export const searchApi = {
  search: (params: { q: string; providers?: string[]; kind?: string; year?: number; cursor?: string }) =>
    http.get<SearchResponse>('/search', {
      q: params.q,
      providers: params.providers?.join(','),
      kind: params.kind,
      year: params.year,
      cursor: params.cursor,
    }),
  providers: () => http.get<{ providers: Provider[] }>('/search/providers'),
  detail: (providerId: string, ref: string) =>
    http.get<CandidateDetail>(`/resources/${providerId}/${encodeURIComponent(ref)}`),
}

export const actionApi = {
  create: (providerId: string, ref: string, kind: string, targetDir?: string | null) =>
    http.post<{ actionId: string; status: string }>(
      `/resources/${providerId}/${encodeURIComponent(ref)}/actions`,
      { kind, targetDir: targetDir ?? null },
    ),
  get: (actionId: string) => http.get<ActionRecord>(`/actions/${actionId}`),
  list: (cursor?: string, limit = 20) =>
    http.get<Page & { actions: ActionRecord[] }>('/actions', { cursor, limit }),
  cancel: (actionId: string) => http.post<ActionRecord>(`/actions/${actionId}/cancel`),
}

export const libraryApi = {
  items: (params: { sort?: 'recent' | 'title'; q?: string; cursor?: string; limit?: number } = {}) =>
    http.get<Page & { items: MediaItem[] }>('/library/items', params),
  item: (id: string) => http.get<MediaItemDetail>(`/library/items/${id}`),
  dirs: (path?: string | null) => http.get<DirsResponse>('/library/dirs', { path }),
  continueWatching: () => http.get<{ items: MediaItem[] }>('/library/continue'),
  playInfo: (id: string) => http.post<PlayInfo>(`/library/items/${id}/play-info`),
  putProgress: (id: string, positionSeconds: number) =>
    http.put<{ progressSeconds: number; lastPlayedAt: number }>(`/library/items/${id}/progress`, {
      positionSeconds,
      clientTimestamp: Math.floor(Date.now() / 1000),
    }),
  putFavorite: (id: string, favorite: boolean) =>
    http.put<{ favorite: boolean }>(`/library/items/${id}/favorite`, { favorite }),
}

export const preferencesApi = {
  get: () => http.get<Preferences>('/preferences'),
  update: (patch: Partial<Preferences>) => http.put<Preferences>('/preferences', patch),
  saveIconLibraries: (libraries: IconLibrary[]) =>
    http.put<Preferences>('/preferences/icon-libraries', { libraries }),
  /** 取某个图标库的全部条目（名称 → 图片地址），供头像选择器预览。 */
  iconLibraryIcons: (url: string) =>
    http.get<{ name: string; url: string }[]>('/preferences/icon-libraries/icons', { url }),
  saveNetwork: (proxy: NetworkProxy) => http.put<Preferences>('/preferences/network', { proxy }),
  saveBasic: (basic: BasicSettings) => http.put<Preferences>('/preferences/basic', basic),
  saveGithub: (github: GithubSettings) => http.put<Preferences>('/preferences/github', github),
  saveAdvanced: (advanced: AdvancedSettings) =>
    http.put<Preferences>('/preferences/advanced', advanced),
  rotateToken: (apiToken: string) => http.put<Preferences>('/preferences/token', { apiToken }),
  savePlugins: (plugins: PluginSettings) =>
    http.put<Preferences>('/preferences/plugins', plugins),
  saveQbittorrent: (qbittorrent: QbittorrentSettings) =>
    http.put<Preferences>('/preferences/qbittorrent', qbittorrent),
  /** 用表单里填的值试连下载器，不落库。 */
  testQbittorrent: (qbittorrent: QbittorrentSettings) =>
    http.post<QbittorrentTestResult>('/preferences/qbittorrent/test', qbittorrent),
  saveMoviepilot: (moviepilot: MoviepilotSettings) =>
    http.put<Preferences>('/preferences/moviepilot', moviepilot),
  /** 读 MoviePilot 与它名下下载器的运行概况，只查询不改对方流程。 */
  moviepilotStatus: () => http.get<MoviepilotStatus>('/preferences/moviepilot/status'),
  /** 用表单里填的值试连 MoviePilot，不落库。 */
  testMoviepilot: (moviepilot: MoviepilotSettings) =>
    http.post<MoviepilotStatus>('/preferences/moviepilot/test', moviepilot),
  githubAuthStatus: () => http.get<GithubAuthStatus>('/preferences/github/auth/status'),
  startGithubAuth: () => http.post<GithubDeviceAuthStart>('/preferences/github/auth/start'),
  pollGithubAuth: (sessionId: string) =>
    http.post<GithubDeviceAuthPoll>('/preferences/github/auth/poll', { sessionId }),
  saveGithubManualToken: (token: string) =>
    http.post<GithubAuthStatus>('/preferences/github/auth/manual', { token }),
  clearGithubToken: () => http.delete<void>('/preferences/github/auth/token'),
}

export type PluginConfig = {
  enabled: boolean
  apiKey: string
}

export const metaApi = {
  boards: () => http.get<MetaBoardsResponse>('/meta/boards'),
  discover: (params: {
    source: MetaSource
    kind: MetaKind
    category?: string
    page?: number
  }) => http.get<MetaDiscoverResponse>('/meta/discover', params),
  detail: (source: MetaSource, id: string, kind: MetaKind) =>
    http.get<MetaDetail>(`/meta/${source}/${encodeURIComponent(id)}`, { kind }),
}

export const pluginsApi = {
  installed: () => http.get<{ plugins: PluginItem[] }>('/plugins/installed'),
  market: () => http.get<{ plugins: PluginItem[] }>('/plugins/market'),
  get: (id: string) => http.get<PluginItem>(`/plugins/${id}`),
  /** 安装时服务端下载 iconUrl 到本地，之后已安装页不再联网取图 */
  install: (payload: PluginInstall) => http.post<PluginItem>('/plugins/install', payload),
  uninstall: (id: string) => http.delete<void>(`/plugins/${id}`),
  patch: (id: string, payload: { enabled?: boolean }) =>
    http.patch<PluginItem>(`/plugins/${id}`, payload),
  config: (id: string) => http.get<PluginConfig>(`/plugins/${id}/config`),
  saveConfig: (id: string, payload: Partial<PluginConfig>) =>
    http.put<PluginConfig>(`/plugins/${id}/config`, payload),
}

export const sitesApi = {
  list: () => http.get<{ sites: Site[] }>('/sites'),
  get: (id: number) => http.get<Site>(`/sites/${id}`),
  create: (payload: SiteWrite) => http.post<Site>('/sites', payload),
  /** 按站点地址抓首页标题取站名，添加站点时自动填入；proxy 跟随站点代理开关 */
  meta: (url: string, ua = '', proxy = false) =>
    http.get<SiteMeta>('/sites/meta', { url, ua, proxy: String(proxy) }),
  update: (id: number, payload: SiteWrite) => http.put<Site>(`/sites/${id}`, payload),
  patch: (id: number, payload: SitePatch) => http.patch<Site>(`/sites/${id}`, payload),
  remove: (id: number) => http.delete<void>(`/sites/${id}`),
  /** 兼容 MoviePilot 导出 JSON 的单条导入 */
  importOne: (raw: Record<string, unknown>) => http.post<Site>('/sites/import', raw),
  statistics: () => http.get<{ stats: SiteStatistic[] }>('/sites/statistics'),
  /** 单站点统计；未测过时返回全零 */
  statisticByDomain: (domain: string) =>
    http.get<SiteStatistic>(`/sites/statistics/${encodeURIComponent(domain)}`),
  test: (id: number) => http.get<SiteTestResult>(`/sites/${id}/test`),
  /** 用关键词试搜一次，确认站点能被解析出种子 */
  probe: (id: number, q: string) =>
    http.get<SiteProbeResult>(`/sites/${id}/probe?q=${encodeURIComponent(q)}`),
  updatePriorities: (items: { id: number; pri: number }[]) =>
    http.put<{ sites: Site[] }>('/sites/priorities', { items }),
}

export type { TokenPair }
