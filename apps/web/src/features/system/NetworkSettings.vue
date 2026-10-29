<script setup lang="ts">
// 基础设定（系统 → 设定 → 基础设定）：整块收进一张卡片，卡内只放必需项与入口行。
// GitHub / MoviePilot / 应用助手 / 高级配置一律弹窗处理，避免展开时撑破卡片布局（docs/02 §9.3）。
// GitHub 走设备码授权（docs/07 §2.8.1）：点「开始授权」拿短码，用户在 GitHub 输入，前端按服务端给的间隔轮询。
// MoviePilot 承担搜索、识别、整理、加种的全流程：本页只读它的运行状态，不提供任何改动它流程的操作。
// 表单 id 由页脚动作条通过 form="network-settings" 关联，保持不动。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'
import { describeError } from '@/core/api/error'
import { preferencesApi } from '@/data/api'
import type {
  AdvancedSettings,
  FilterRule,
  GithubAuthStatus,
  GithubDeviceAuthStart,
  MoviepilotSettings,
  MoviepilotStatus,
  Preferences,
} from '@/domain/contract'

// 代理地址按 MoviePilot 的写法：一个带 scheme 的完整地址
const PROXY_PLACEHOLDER = 'http://127.0.0.1:7890'

// MoviePilot 地址按后端端口填，3000 是它默认的后端监听端口
const MP_PLACEHOLDER = 'http://192.168.2.38:3000'

/** 读状态失败时的兜底值，让卡片仍能渲染成离线态 */
const EMPTY_MP_STATUS: MoviepilotStatus = {
  ok: false,
  message: '',
  sites: [],
  downloader: '',
  downloaderType: '',
  dlSpeed: null,
  upSpeed: null,
  dlTotal: null,
  upTotal: null,
  freeSpace: null,
  totalSpace: null,
  usedSpace: null,
  activeTasks: 0,
  jobs: [],
  jobTotal: 0,
  connectionStatus: 'disconnected',
}

/** 过滤规则只给内置档位，用分段控件代替下拉，选项一眼可见 */
const FILTER_RULES: { value: FilterRule; label: string }[] = [
  { value: 'off', label: '不过滤' },
  { value: 'basic', label: '基础去重' },
  { value: 'strict', label: '严格匹配' },
]

/** 高级配置弹窗的分栏；分组较多，一次只展示一栏 */
const DIALOG_TABS = [
  { key: 'search', label: '搜索与缓存' },
  { key: 'network', label: '网络代理' },
  { key: 'request', label: '请求策略' },
] as const

type DialogTab = (typeof DIALOG_TABS)[number]['key']

const loading = ref(true)
const errorText = ref('')
const saving = ref(false)
const saveError = ref('')
const saved = ref(false)

// ---- 页面上的必需项
const lanUrl = ref('')
const bridgeUrl = ref('')
const apiToken = ref('')

// ---- 弹窗内的其余参数
const filterRule = ref<FilterRule>('basic')
const doubanCache = ref(true)
const enabled = ref(false)
const host = ref(PROXY_PLACEHOLDER)
const ghProxy = ref('')
const advanced = ref<AdvancedSettings>({ requestTimeout: 15, concurrency: 8 })

// ---- MoviePilot：自动化流程全交给它，本页只读状态；改动先落本地，弹窗内单独保存
const mp = ref<MoviepilotSettings>({ enabled: false, url: '', token: '' })
const mpOpen = ref(false)
const qbTesting = ref(false)
const qbTestMsg = ref('')
const qbTestOk = ref(false)
// 卡片上的运行概况：页面停留时每 30 秒静默刷新一次，切走标签页则暂停
const mpStatus = ref<MoviepilotStatus | null>(null)
const mpLoading = ref(false)
let mpTimer: ReturnType<typeof setInterval> | null = null

/** 字节/秒 → `1.2 MB/s`，下载器卡片与试连结果共用 */
function formatSpeed(bytes: number | null): string {
  if (bytes === null || bytes < 0) return '—'
  const units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${index === 0 ? value : value.toFixed(1)} ${units[index]}`
}

/** 字节 → `428.0 GB`，用于累计流量与磁盘容量 */
function formatSize(bytes: number | null): string {
  if (bytes === null || bytes < 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${index === 0 ? value : value.toFixed(1)} ${units[index]}`
}

/** 媒体库存储占用百分比；缺任一边就返回空，避免显示假的 0% */
const mpDiskPercent = computed<number | null>(() => {
  const total = mpStatus.value?.totalSpace
  const used = mpStatus.value?.usedSpace
  if (!total || used === null || used === undefined) return null
  return Math.min(100, Math.round((used / total) * 100))
})

/** 磁盘吃紧时卡片要变红，80% 是 PT 做种的常规警戒线 */
const mpDiskTight = computed(() => (mpDiskPercent.value ?? 0) >= 80)

/** 取 MoviePilot 与它名下下载器的运行概况；失败时只标记离线，保留卡片结构 */
async function refreshMoviepilot(): Promise<void> {
  if (!mp.value.enabled || !mp.value.url.trim()) {
    mpStatus.value = null
    return
  }
  mpLoading.value = true
  try {
    mpStatus.value = await preferencesApi.moviepilotStatus()
  } catch {
    mpStatus.value = { ...EMPTY_MP_STATUS, message: '无法读取 MoviePilot 状态' }
  } finally {
    mpLoading.value = false
  }
}

/** 30 秒轮询：页面不可见时不打接口，回来立刻补一次 */
function startMoviepilotPoll(): void {
  stopMoviepilotPoll()
  mpTimer = setInterval(() => {
    if (document.visibilityState === 'visible') void refreshMoviepilot()
  }, 30_000)
}

function stopMoviepilotPoll(): void {
  if (mpTimer) {
    clearInterval(mpTimer)
    mpTimer = null
  }
}

/** 从后台切回来时补一次，避免看到离开前的旧数字 */
function onVisibilityChange(): void {
  if (document.visibilityState === 'visible' && mp.value.enabled) void refreshMoviepilot()
}

// ---- GitHub 授权：状态由服务端裁决，前端只保存展示用的摘要
const ghAuth = ref<GithubAuthStatus | null>(null)
const ghSession = ref<GithubDeviceAuthStart | null>(null)
const ghBusy = ref(false)
const ghError = ref('')
const ghNotice = ref('')
const ghManual = ref('')
let ghTimer: ReturnType<typeof setTimeout> | null = null

// 上次保存的值，用来算 dirty 与重置
const savedSnapshot = ref('')
const draft = ref<Preferences | null>(null)

// 入口行只露摘要；详情一律弹窗，不在卡片内展开
const githubOpen = ref(false)
const assistantOpen = ref(false)
const revokeOpen = ref(false)

// 高级配置弹窗：改动先落在本地，随页脚保存一起提交
const advancedOpen = defineModel<boolean>('advancedOpen', { default: false })

// 每次打开弹窗都回到第一栏，避免上次停留的栏位让人误以为参数丢了
const dialogTab = ref<DialogTab>('search')
watch(advancedOpen, (open) => {
  if (open) dialogTab.value = 'search'
})
watch(githubOpen, (open) => {
  if (!open) {
    cancelGithubAuth()
    ghManual.value = ''
    ghError.value = ''
  }
})
// 关掉 MoviePilot 弹窗就清掉上次的试连结果，避免下次打开看到过期提示
watch(mpOpen, (open) => {
  if (!open) {
    qbTestMsg.value = ''
    qbTestOk.value = false
  }
})

const snapshot = computed(() =>
  JSON.stringify([
    lanUrl.value,
    bridgeUrl.value,
    apiToken.value,
    filterRule.value,
    doubanCache.value,
    enabled.value,
    host.value,
    ghProxy.value,
    advanced.value.requestTimeout,
    advanced.value.concurrency,
    mp.value.enabled,
    mp.value.url,
    mp.value.token,
  ]),
)

const dirty = computed(() => snapshot.value !== savedSnapshot.value)

// ---- GitHub 折叠行的摘要：一行字说清「谁、还灵不灵」
const ghStateText = computed(() => {
  const auth = ghAuth.value
  if (!auth?.configured) return '未授权'
  if (auth.valid === false) return '已失效'
  if (auth.needsReauthorization) return '需重新授权'
  return '已授权'
})

const ghSummary = computed(() => {
  const auth = ghAuth.value
  if (!auth?.configured) return '未授权'
  const parts = [auth.login || '未知账号', auth.maskedToken || '—']
  return parts.join(' · ')
})

const ghChipOff = computed(
  () => !ghAuth.value?.configured || ghAuth.value.valid === false || ghAuth.value.needsReauthorization,
)

const ghSourceText = computed(() => {
  const auth = ghAuth.value
  if (!auth?.configured) return ''
  if (auth.source === 'oauth') return '设备码授权'
  if (auth.source === 'manual') return '手动令牌'
  return ''
})

function apply(preferences: Preferences): void {
  draft.value = preferences
  lanUrl.value = preferences.basic.lanUrl
  bridgeUrl.value = preferences.basic.bridgeUrl
  apiToken.value = preferences.apiToken
  filterRule.value = preferences.basic.filterRule
  doubanCache.value = preferences.basic.doubanCache
  enabled.value = preferences.network.proxy.enabled
  host.value = preferences.network.proxy.host
  ghProxy.value = preferences.github.proxy
  advanced.value = { ...preferences.advanced }
  mp.value = { ...preferences.moviepilot }
  savedSnapshot.value = snapshot.value
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    apply(await preferencesApi.get())
    // 授权状态单独取：失效判定要打一次 GitHub，失败也不该挡住整页
    void refreshGithubAuth()
    // 下载器速度只影响卡片展示，失败也要让整页正常出来
    void refreshMoviepilot()
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

async function refreshGithubAuth(): Promise<void> {
  try {
    ghAuth.value = await preferencesApi.githubAuthStatus()
  } catch (error) {
    ghError.value = describeError(error)
  }
}

/** 轮询收尾：清掉定时器与会话，避免离开页面后还在打接口 */
function stopGithubPoll(): void {
  if (ghTimer) {
    clearTimeout(ghTimer)
    ghTimer = null
  }
}

/** 服务端裁决节奏：拿到 retryAfter 才安排下一次，前端不自己猜间隔 */
function scheduleGithubPoll(seconds: number): void {
  stopGithubPoll()
  ghTimer = setTimeout(() => void pollGithubAuth(), Math.max(seconds, 1) * 1000)
}

async function startGithubAuth(): Promise<void> {
  ghBusy.value = true
  ghError.value = ''
  ghNotice.value = ''
  try {
    ghSession.value = await preferencesApi.startGithubAuth()
    // 与 MoviePilot 一致：在点击的同一上下文里打开验证页，随后立即开轮询
    openGithubVerifyPage()
    void pollGithubAuth()
  } catch (error) {
    ghError.value = describeError(error)
  } finally {
    ghBusy.value = false
  }
}

/** 弹窗被拦时退回新标签页；仍失败就只剩面板里的链接可用 */
function openGithubVerifyPage(): void {
  const uri = ghSession.value?.verificationUri
  if (!uri) return
  if (window.open(uri, '_blank', 'noopener,noreferrer')) return
  ghNotice.value = '无法自动打开 GitHub，请点上面的链接手动打开。'
}

async function pollGithubAuth(): Promise<void> {
  const session = ghSession.value
  if (!session) return
  try {
    const result = await preferencesApi.pollGithubAuth(session.sessionId)
    if (result.state === 'authorized') {
      stopGithubPoll()
      ghSession.value = null
      ghAuth.value = result.status
      ghNotice.value = result.message
      return
    }
    if (result.state === 'pending' || result.state === 'slow_down') {
      ghNotice.value = result.message
      scheduleGithubPoll(result.retryAfter ?? session.intervalSeconds)
      return
    }
    // denied / expired / failed 都是终止态，重新开始即可
    stopGithubPoll()
    ghSession.value = null
    ghError.value = result.message
  } catch (error) {
    stopGithubPoll()
    ghSession.value = null
    ghError.value = describeError(error)
  }
}

function cancelGithubAuth(): void {
  stopGithubPoll()
  ghSession.value = null
  ghNotice.value = ''
}

async function submitManualToken(): Promise<void> {
  const token = ghManual.value.trim()
  if (!token) {
    ghError.value = '请填写 GitHub 令牌'
    return
  }
  ghBusy.value = true
  ghError.value = ''
  ghNotice.value = ''
  try {
    ghAuth.value = await preferencesApi.saveGithubManualToken(token)
    ghManual.value = ''
    ghNotice.value = '令牌已保存'
  } catch (error) {
    ghError.value = describeError(error)
  } finally {
    ghBusy.value = false
  }
}

/** 解除授权用独立确认弹窗，避免与 GitHub 弹窗叠层抢 Esc */
function askRevokeGithub(): void {
  githubOpen.value = false
  revokeOpen.value = true
}

function cancelRevokeGithub(): void {
  revokeOpen.value = false
  githubOpen.value = true
}

async function revokeGithubAuth(): Promise<void> {
  ghBusy.value = true
  ghError.value = ''
  ghNotice.value = ''
  try {
    await preferencesApi.clearGithubToken()
    ghAuth.value = await preferencesApi.githubAuthStatus()
    ghNotice.value = '已解除授权'
    revokeOpen.value = false
    githubOpen.value = true
  } catch (error) {
    ghError.value = describeError(error)
  } finally {
    ghBusy.value = false
  }
}

async function copyUserCode(): Promise<void> {
  if (!ghSession.value) return
  try {
    await navigator.clipboard.writeText(ghSession.value.userCode)
    ghNotice.value = '短码已复制'
  } catch {
    ghError.value = '浏览器拒绝了剪贴板访问，请手动选中复制'
  }
}

async function submit(): Promise<void> {
  if (!dirty.value) return
  if (enabled.value && !host.value.trim()) {
    saveError.value = '启用代理时地址不能为空'
    return
  }
  if (bridgeUrl.value.trim() && !/^https?:\/\//i.test(bridgeUrl.value.trim())) {
    saveError.value = '反代地址需以 http:// 或 https:// 开头'
    return
  }
  if (mp.value.enabled && !mp.value.url.trim()) {
    saveError.value = '启用 MoviePilot 时地址不能为空'
    return
  }
  if (mp.value.url.trim() && !/^https?:\/\//i.test(mp.value.url.trim())) {
    saveError.value = 'MoviePilot 地址需以 http:// 或 https:// 开头'
    return
  }
  saving.value = true
  saveError.value = ''
  saved.value = false
  try {
    // 四段各自独立，逐段写入后以最后一次返回为准
    let preferences = await preferencesApi.saveBasic({
      lanUrl: lanUrl.value.trim(),
      bridgeUrl: bridgeUrl.value.trim(),
      filterRule: filterRule.value,
      doubanCache: doubanCache.value,
      backgroundImage: draft.value?.basic.backgroundImage ?? '',
    })
    if (apiToken.value.trim() !== preferences.apiToken) {
      preferences = await preferencesApi.rotateToken(apiToken.value.trim())
    }
    preferences = await preferencesApi.saveNetwork({ enabled: enabled.value, host: host.value.trim() })
    preferences = await preferencesApi.saveGithub({
      proxy: ghProxy.value.trim(),
      token: draft.value?.github.token ?? '',
      user: draft.value?.github.user ?? '',
    })
    preferences = await preferencesApi.saveAdvanced(advanced.value)
    preferences = await preferencesApi.saveMoviepilot({
      ...mp.value,
      url: mp.value.url.trim(),
      token: mp.value.token.trim(),
    })
    apply(preferences)
    saved.value = true
    if (mp.value.enabled) void refreshMoviepilot()
  } catch (error) {
    saveError.value = describeError(error)
  } finally {
    saving.value = false
  }
}

/** 重置：回到上次保存的值，不落库 */
function reset(): void {
  savedSnapshot.value = ''
  saveError.value = ''
  saved.value = false
  if (draft.value) apply(draft.value)
  else void load()
}

/** 试连 MoviePilot：用当前表单值，不落库，方便保存前先确认地址与令牌 */
async function testMoviepilot(): Promise<void> {
  qbTesting.value = true
  qbTestMsg.value = ''
  qbTestOk.value = false
  try {
    const result = await preferencesApi.testMoviepilot({
      ...mp.value,
      url: mp.value.url.trim(),
      token: mp.value.token.trim(),
    })
    qbTestOk.value = result.ok
    qbTestMsg.value = result.ok
      ? `连接正常 · ${result.downloader || '无下载器'} · ${result.sites.length} 个站点`
      : result.message
  } catch (error) {
    qbTestMsg.value = describeError(error)
  } finally {
    qbTesting.value = false
  }
}

/** 弹窗内单独保存 MoviePilot：它有自己的弹窗，不该依赖外层表单的提交 */
async function saveMoviepilot(): Promise<void> {
  if (mp.value.enabled && !mp.value.url.trim()) {
    qbTestOk.value = false
    qbTestMsg.value = '启用 MoviePilot 时地址不能为空'
    return
  }
  if (mp.value.url.trim() && !/^https?:\/\//i.test(mp.value.url.trim())) {
    qbTestOk.value = false
    qbTestMsg.value = '地址需以 http:// 或 https:// 开头'
    return
  }
  saving.value = true
  qbTestMsg.value = ''
  try {
    const preferences = await preferencesApi.saveMoviepilot({
      ...mp.value,
      url: mp.value.url.trim(),
      token: mp.value.token.trim(),
    })
    apply(preferences)
    mpOpen.value = false
    void refreshMoviepilot()
  } catch (error) {
    qbTestOk.value = false
    qbTestMsg.value = describeError(error)
  } finally {
    saving.value = false
  }
}

async function copyToken(): Promise<void> {
  if (!apiToken.value) return
  try {
    await navigator.clipboard.writeText(apiToken.value)
    saved.value = true
  } catch {
    saveError.value = '浏览器拒绝了剪贴板访问，请手动选中复制'
  }
}

onMounted(() => {
  void load()
  startMoviepilotPoll()
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onBeforeUnmount(() => {
  stopGithubPoll()
  stopMoviepilotPoll()
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <AppErrorState v-if="errorText" :message="errorText" @retry="load" />

  <SysStyles v-else>
    <form id="network-settings" class="basic" novalidate @submit.prevent="submit" @reset.prevent="reset">
      <section class="group">
        <!-- 整块基础设定收进一张卡片：卡片头带标题与入口，卡身放三项必需配置 -->
        <div class="card">
          <header class="card__head">
            <div class="card__head-main">
              <h2 class="card__title">基础设定</h2>
              <p class="card__desc">内网访问与接口调用所需</p>
            </div>
            <button type="button" class="card__action" @click="advancedOpen = true">
              <AppIcon name="sliders" :size="14" />高级配置
            </button>
          </header>

          <div v-if="loading" class="card__body">
            <AppSkeleton height="16px" width="220px" />
          </div>

          <div v-else class="card__body">
            <!-- 三项必需配置并排一行，宽度均分；宽屏下不再拉出超长输入框 -->
            <div class="field__grid">
              <div class="field">
                <div class="field__head">
                  <span id="lan-label" class="field__label">内网地址</span>
                  <span class="field__hint">主机:端口</span>
                </div>
                <span class="field__control is-mono">
                  <input
                    v-model="lanUrl"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    aria-labelledby="lan-label"
                    placeholder="192.168.2.38:3000"
                    :disabled="saving"
                  />
                </span>
              </div>

              <div class="field">
                <div class="field__head">
                  <span id="bridge-label" class="field__label">反代地址</span>
                  <span class="field__hint">带 http(s)://</span>
                </div>
                <span class="field__control is-mono">
                  <input
                    v-model="bridgeUrl"
                    type="url"
                    autocomplete="off"
                    spellcheck="false"
                    aria-labelledby="bridge-label"
                    placeholder="https://rex.115rex.cn"
                    :disabled="saving"
                  />
                </span>
              </div>

              <div class="field field--wide">
                <div class="field__head">
                  <span id="token-label" class="field__label">API 令牌</span>
                  <span class="field__hint">客户端凭证</span>
                </div>
                <span class="field__control is-mono field__control--joined">
                  <input
                    v-model="apiToken"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    aria-labelledby="token-label"
                    :disabled="saving"
                  />
                  <button type="button" class="field__icon-btn" aria-label="复制 API 令牌" :disabled="!apiToken" @click="copyToken">
                    <AppIcon name="copy" :size="16" />
                  </button>
                </span>
              </div>
            </div>

            <!-- 入口行：左主信息（标题+状态 / 说明）右动作，等高贴齐动作条 -->
            <div class="entries">
              <div class="entry">
                <AppIcon name="github" :size="18" class="entry__icon" />
                <div class="entry__main">
                  <div class="entry__title-row">
                    <span class="entry__title">GitHub 授权</span>
                    <span class="chip" :class="{ 'is-off': ghChipOff }">{{ ghStateText }}</span>
                  </div>
                  <span class="entry__desc">插件市场、镜像库与更新检测</span>
                </div>
                <span v-if="ghSummary" class="entry__value">{{ ghSummary }}</span>
                <AppButton size="sm" @click="githubOpen = true">打开配置</AppButton>
              </div>

              <div class="entry">
                <AppIcon name="robot" :size="18" class="entry__icon" />
                <div class="entry__main">
                  <div class="entry__title-row">
                    <span class="entry__title">应用助手配置</span>
                    <span class="chip is-off">未启用</span>
                  </div>
                  <span class="entry__desc">内置 Agent 能力，或接入自有模型</span>
                </div>
                <AppButton size="sm" @click="assistantOpen = true">打开配置</AppButton>
              </div>
            </div>
          </div>

          <footer class="card__actions">
            <div class="card__status">
              <p v-if="saveError" class="row__error">{{ saveError }}</p>
              <p v-else-if="saved" class="row__note">已保存</p>
              <p v-else-if="dirty" class="row__note">有未保存的改动</p>
            </div>
            <div class="card__buttons">
              <AppButton size="sm" type="reset" :disabled="saving || !dirty">重置配置</AppButton>
              <AppButton size="sm" variant="primary" type="submit" :disabled="saving || !dirty">保存</AppButton>
            </div>
          </footer>
        </div>

        <!-- MoviePilot 单独一张卡：搜索、识别、整理、加种都由它跑，这里只读它的运行状态 -->
        <div class="card">
          <header class="card__head">
            <div class="card__head-main">
              <h2 class="card__title">MoviePilot</h2>
              <p class="card__desc">下载与整理流程由 MoviePilot 自己执行，这里只读取状态。</p>
            </div>
          </header>

          <div class="card__body">
            <button
              v-if="mp.enabled && mp.url.trim()"
              type="button"
              class="mp-tile"
              @click="mpOpen = true"
            >
              <span class="mp-tile__logo" aria-hidden="true">
                <img class="mp-tile__mark" src="/moviepilot-logo.svg" width="44" height="44" alt="" />
                <span
                  class="mp-tile__dot"
                  :class="{
                    'is-on': mpStatus?.connectionStatus === 'connected',
                    'is-warn': mpStatus?.connectionStatus === 'firewalled',
                    'is-off': !mpStatus || !mpStatus.ok,
                  }"
                />
              </span>

              <span class="mp-tile__main">
                <div class="mp-tile__head">
                  <span class="mp-tile__title">MoviePilot</span>
                  <span v-if="mpStatus?.downloader" class="mp-tile__badge">
                    {{ mpStatus.downloader }}
                  </span>
                  <span
                    class="mp-tile__remove"
                    role="button"
                    aria-label="关闭 MoviePilot"
                    @click.stop="mp.enabled = false"
                  >
                    <AppIcon name="close" :size="13" />
                  </span>
                </div>

                <div class="mp-tile__row tabular">
                  <span class="mp-tile__metric">
                    <span class="mp-tile__metric-key">↓</span>
                    {{ mpLoading ? '…' : formatSpeed(mpStatus?.dlSpeed ?? null) }}
                  </span>
                  <span class="mp-tile__divider" aria-hidden="true" />
                  <span class="mp-tile__metric">
                    <span class="mp-tile__metric-key">↑</span>
                    {{ mpLoading ? '…' : formatSpeed(mpStatus?.upSpeed ?? null) }}
                  </span>
                </div>

                <div v-if="mpStatus?.ok" class="mp-tile__row mp-tile__row--muted tabular">
                  <span :class="{ 'mp-meta__bad': mpDiskTight }">
                    磁盘 {{ formatSize(mpStatus?.freeSpace ?? null) }} 可用<template v-if="mpDiskPercent !== null">（{{ mpDiskPercent }}%）</template>
                  </span>
                </div>
                <div v-if="mpStatus?.ok" class="mp-tile__row mp-tile__row--muted tabular">
                  <span>累计 ↓{{ formatSize(mpStatus?.dlTotal ?? null) }} ↑{{ formatSize(mpStatus?.upTotal ?? null) }}</span>
                </div>
              </span>
            </button>

            <button v-else type="button" class="qb-add" @click="mpOpen = true">
              <AppIcon name="plus" :size="16" />
            </button>
          </div>

          <footer class="card__actions">
            <div class="card__status">
              <p v-if="!mp.enabled" class="row__note">未接入 MoviePilot，站点搜索不会自动推送</p>
              <p v-else-if="mpStatus && !mpStatus.ok" class="row__note">{{ mpStatus.message }}</p>
              <p v-else-if="mpStatus" class="row__note">
                {{ mpStatus.sites.length }} 个站点 · {{ mpStatus.activeTasks }} 个任务下载中 ·
                <span v-if="mpStatus.jobs.length" class="mp-meta__bad">
                  {{ mpStatus.jobs.length }} 个后台任务异常
                </span>
                <span v-else>后台任务正常</span>
              </p>
              <p v-if="mpStatus?.jobs.length" class="row__error">
                <span v-for="job in mpStatus.jobs" :key="job.id">
                  {{ job.name }}：{{ job.error || '最近一次执行失败' }}<br />
                </span>
              </p>
            </div>
            <div class="card__buttons">
              <AppButton size="sm" @click="refreshMoviepilot" :disabled="!mp.enabled || mpLoading">刷新状态</AppButton>
              <AppButton size="sm" variant="primary" @click="mpOpen = true">配置</AppButton>
            </div>
          </footer>
        </div>
      </section>
    </form>

    <AppDialog
      v-model:open="advancedOpen"
      title="高级配置"
      description="这些参数不影响日常使用，改动随页面保存一起提交"
      size="md"
    >
      <div class="sheet">
        <nav class="sheet-tabs" role="tablist" aria-label="高级配置分组">
          <button
            v-for="item in DIALOG_TABS"
            :key="item.key"
            type="button"
            class="sheet-tabs__item"
            :class="{ 'is-active': dialogTab === item.key }"
            role="tab"
            :aria-selected="dialogTab === item.key"
            @click="dialogTab = item.key"
          >
            {{ item.label }}
          </button>
        </nav>

        <fieldset v-if="dialogTab === 'search'" class="sheet-panel">
          <div class="sheet-row sheet-row--stack">
            <span class="sheet-label">默认过滤规则</span>
            <span class="segmented segmented--fill" role="radiogroup" aria-label="默认过滤规则">
              <button
                v-for="item in FILTER_RULES"
                :key="item.value"
                type="button"
                class="segmented__item"
                :class="{ 'is-active': filterRule === item.value }"
                role="radio"
                :aria-checked="filterRule === item.value"
                @click="filterRule = item.value"
              >
                {{ item.label }}
              </button>
            </span>
          </div>
          <label class="sheet-row">
            <span class="sheet-label">
              豆瓣缓存
              <span class="sheet-hint">缓存影片元数据，减少重复请求</span>
            </span>
            <span class="switch">
              <input v-model="doubanCache" type="checkbox" />
              <span class="switch__track" aria-hidden="true" />
            </span>
          </label>
        </fieldset>

        <fieldset v-else-if="dialogTab === 'network'" class="sheet-panel">
          <label class="sheet-row">
            <span class="sheet-label">
              启用代理
              <span class="sheet-hint">关闭时代理配置保留但不再生效</span>
            </span>
            <span class="switch">
              <input v-model="enabled" type="checkbox" />
              <span class="switch__track" aria-hidden="true" />
            </span>
          </label>
          <label class="sheet-row sheet-row--stack">
            <span class="sheet-label">代理服务器</span>
            <input
              v-model="host"
              class="sheet-input"
              type="text"
              :placeholder="PROXY_PLACEHOLDER"
              :disabled="!enabled"
            />
          </label>
          <label class="sheet-row sheet-row--stack">
            <span class="sheet-label">
              GitHub 加速地址
              <span class="sheet-hint">插件市场与仓库下载走这里，留空则直连</span>
            </span>
            <input
              v-model="ghProxy"
              class="sheet-input"
              type="text"
              autocomplete="off"
              spellcheck="false"
              placeholder="https://ghproxy.example"
            />
          </label>
        </fieldset>

        <fieldset v-else class="sheet-panel">
          <label class="sheet-row">
            <span class="sheet-label">
              请求超时
              <span class="sheet-hint">单次出站请求的最长等待（秒）</span>
            </span>
            <input
              v-model.number="advanced.requestTimeout"
              class="sheet-input sheet-input--num"
              type="number"
              min="1"
              max="120"
            />
          </label>
          <label class="sheet-row">
            <span class="sheet-label">
              并发数
              <span class="sheet-hint">同时进行的上游请求上限</span>
            </span>
            <input
              v-model.number="advanced.concurrency"
              class="sheet-input sheet-input--num"
              type="number"
              min="1"
              max="64"
            />
          </label>
        </fieldset>
      </div>

      <template #footer>
        <AppButton size="sm" @click="advancedOpen = false">取消</AppButton>
        <AppButton size="sm" variant="primary" @click="advancedOpen = false">完成</AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="githubOpen"
      title="GitHub 授权"
      description="用于插件市场、镜像库与更新检测。"
      size="md"
    >
      <div class="gh">
        <!-- 设备码进行中：突出短码，其它入口先让路 -->
        <template v-if="ghSession">
          <ol class="gh__steps">
            <li>
              打开
              <a class="gh__link" :href="ghSession.verificationUri" target="_blank" rel="noopener noreferrer">
                {{ ghSession.verificationUri }}
              </a>
              并输入下面的短码
            </li>
            <li>在 GitHub 页面确认授权，本页会自动完成</li>
          </ol>
          <div class="gh__code">
            <code class="gh__code-value">{{ ghSession.userCode }}</code>
            <button type="button" class="field__icon-btn" aria-label="复制短码" @click="copyUserCode">
              <AppIcon name="copy" :size="16" />
            </button>
          </div>
          <div class="gh__ops">
            <span v-if="ghNotice" class="gh__note">{{ ghNotice }}</span>
            <AppButton size="sm" @click="cancelGithubAuth">取消授权</AppButton>
          </div>
        </template>

        <!-- 已授权 / 未授权：状态卡 + 主操作 -->
        <template v-else>
          <div
            class="gh__status"
            :class="{ 'is-off': ghAuth?.configured && (ghAuth.valid === false || ghAuth.needsReauthorization) }"
          >
            <span class="gh__badge" aria-hidden="true">
              <AppIcon name="github" :size="20" />
            </span>
            <div class="gh__who">
              <span class="gh__login">
                <template v-if="ghAuth?.configured">
                  {{ ghAuth.login || '未知账号' }}
                  <span class="gh__dot" aria-hidden="true" />
                  <span class="gh__source">{{ ghSourceText }}</span>
                </template>
                <template v-else>尚未接入 GitHub</template>
              </span>
              <span class="gh__meta">
                <template v-if="ghAuth?.configured">
                  {{ ghAuth.maskedToken }}
                  <template v-if="ghAuth.expiresAt"> · {{ new Date(ghAuth.expiresAt * 1000).toLocaleString() }} 到期</template>
                </template>
                <template v-else>授权后可稳定拉取插件市场、镜像与更新</template>
              </span>
            </div>
            <span class="chip" :class="{ 'is-off': ghChipOff }">{{ ghStateText }}</span>
          </div>

          <div class="gh__ops gh__ops--start">
            <AppButton
              v-if="ghAuth?.clientIdConfigured"
              size="sm"
              variant="primary"
              :disabled="ghBusy"
              @click="startGithubAuth"
            >
              {{ ghAuth?.configured ? '重新授权' : '开始设备码授权' }}
            </AppButton>
            <AppButton
              v-if="ghAuth?.configured"
              size="sm"
              :disabled="ghBusy"
              @click="askRevokeGithub"
            >
              解除授权
            </AppButton>
          </div>

          <p v-if="ghAuth?.configured && ghAuth.valid === false" class="row__error">令牌已失效，需要重新授权后才能继续使用。</p>
          <p v-else-if="ghAuth?.configured && ghAuth.valid === null" class="gh__note">暂时连不上 GitHub，未能校验令牌是否仍有效。</p>
          <p v-else-if="ghAuth?.configured && ghAuth.needsReauthorization" class="row__error">授权已过期或权限不足，请重新授权。</p>
          <p v-else-if="!ghAuth?.clientIdConfigured" class="gh__note">
            服务端尚未配置 GitHub OAuth App 的 client_id，可改用下方手动令牌。
          </p>
        </template>

        <!-- 手动令牌：常驻，不折叠 -->
        <section class="gh__manual-panel">
          <header class="gh__manual-head">
            <h3 class="gh__manual-title">手动填写令牌</h3>
            <p class="gh__manual-hint">
              粘贴 Personal Access Token，保存后只存在服务端。需要 Issue、Fork、分支推送与 PR 权限；改工作流还需 workflow。
            </p>
          </header>
          <div class="gh__manual">
            <span class="field__control">
              <AppIcon name="key" :size="16" class="gh__manual-icon" />
              <input
                v-model="ghManual"
                type="password"
                autocomplete="off"
                spellcheck="false"
                placeholder="ghp_… 或 github_pat_…"
                aria-label="GitHub 令牌"
                :disabled="ghBusy || !!ghSession"
              />
            </span>
            <AppButton
              size="sm"
              variant="primary"
              :disabled="ghBusy || !!ghSession || !ghManual.trim()"
              @click="submitManualToken"
            >
              保存令牌
            </AppButton>
          </div>
        </section>

        <p v-if="ghError" class="row__error">{{ ghError }}</p>
        <p v-else-if="ghNotice && !ghSession" class="gh__note">{{ ghNotice }}</p>
      </div>

      <template #footer>
        <AppButton size="sm" variant="primary" @click="githubOpen = false">完成</AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="mpOpen"
      title="MoviePilot"
      description="搜索、识别、整理、加种全部由 MoviePilot 自己执行，这里只填接入参数用于读取状态。"
      size="md"
    >
      <div class="qb">
        <fieldset class="sheet-panel">
          <label class="sheet-row">
            <span class="sheet-label">
              启用 MoviePilot
              <span class="sheet-hint">关闭时配置保留但不再读取状态</span>
            </span>
            <span class="switch">
              <input v-model="mp.enabled" type="checkbox" />
              <span class="switch__track" aria-hidden="true" />
            </span>
          </label>
          <label class="sheet-row sheet-row--stack">
            <span class="sheet-label">
              后端地址
              <span class="sheet-hint">带 http(s)://，填 MoviePilot 后端端口而不是前端端口</span>
            </span>
            <input
              v-model="mp.url"
              class="sheet-input"
              type="text"
              autocomplete="off"
              spellcheck="false"
              :placeholder="MP_PLACEHOLDER"
            />
          </label>
          <label class="sheet-row sheet-row--stack">
            <span class="sheet-label">
              API Token
              <span class="sheet-hint">MoviePilot 设定 → 服务 → API Token，等价超级用户</span>
            </span>
            <input
              v-model="mp.token"
              class="sheet-input"
              type="password"
              autocomplete="new-password"
              spellcheck="false"
            />
          </label>
        </fieldset>

        <div class="qb__ops">
          <span
            v-if="qbTestMsg"
            class="qb__msg"
            :class="{ 'is-ok': qbTestOk, 'is-bad': !qbTestOk }"
          >{{ qbTestMsg }}</span>
          <AppButton size="sm" :loading="qbTesting" @click="testMoviepilot">测试连接</AppButton>
        </div>
      </div>

      <template #footer>
        <AppButton size="sm" @click="mpOpen = false">取消</AppButton>
        <AppButton size="sm" variant="primary" :loading="saving" @click="saveMoviepilot">保存</AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="assistantOpen"
      title="应用助手配置"
      description="内置 Agent 能力，或接入自有模型。"
      size="sm"
    >
      <p class="sheet-empty">助手配置尚未开放，后续版本会在这里接入模型地址与密钥。</p>
      <template #footer>
        <AppButton size="sm" variant="primary" @click="assistantOpen = false">知道了</AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="revokeOpen"
      title="解除 GitHub 授权？"
      description="解除后插件市场、镜像库与更新检测将不可用，可随时重新授权。"
      tone="danger"
      size="sm"
    >
      <template #footer>
        <AppButton size="sm" @click="cancelRevokeGithub">取消</AppButton>
        <AppButton size="sm" variant="danger" :loading="ghBusy" @click="revokeGithubAuth">确认解除</AppButton>
      </template>
    </AppDialog>
  </SysStyles>
</template>

<style scoped>
/* 卡片骨架来自 SysStyles，这里只放本组件独有的排布 */

/* 三项必需配置并排一行；令牌列稍宽，40 位十六进制才放得下 */
.field__grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1.25fr;
  gap: var(--space4);
}

@media (max-width: 1080px) {
  
  .field__grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .field--wide {
    grid-column: 1 / -1;
  }
}

@media (max-width: 720px) {
  .field__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

/* 字段：标签行在上、控件在下，标签行内挤一句话说明 */
.field {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  min-width: 0;
}

.field__head {
  display: flex;
  align-items: baseline;
  gap: var(--space2);
  min-width: 0;
}

.field__label {
  flex: none;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.field__hint {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.field__control {
  display: flex;
  align-items: center;
  gap: var(--space2);
  height: 40px;
  padding: 0 var(--space3);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  box-shadow: inset 0 1px 0 var(--highlight-line);
  transition: border-color var(--duration-micro) ease, box-shadow var(--duration-micro) ease;
}

.field__control:hover {
  border-color: color-mix(in srgb, var(--color-text-secondary) 40%, var(--color-separator));
}

.field__control:focus-within {
  border-color: color-mix(in srgb, var(--color-primary) 40%, var(--color-separator));
  box-shadow: none;
}

.field__control input,
.field__control select {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  background: transparent;
  font: inherit;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
  outline: none;
}

.field__control input::placeholder {
  color: var(--color-text-tertiary);
}

.field__control.is-mono input {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  letter-spacing: 0.01em;
}

.field__control input:disabled {
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.field__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-right: calc(var(--space1) * -1);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition: background-color var(--duration-micro) ease, color var(--duration-micro) ease;
}

.field__control--joined {
  padding-right: 0;
  gap: 0;
}

.field__control--joined input {
  padding-right: var(--space2);
}

.field__control--joined .field__icon-btn {
  height: 100%;
  width: 36px;
  margin-right: 0;
  border-left: 1px solid var(--color-separator);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.field__control--joined .field__icon-btn:hover:not(:disabled) {
  background: var(--color-surface-secondary);
}

.field__icon-btn:hover:not(:disabled) {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.field__icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ---- 入口组：吃掉 card__body 底 padding，双行主信息 + 右动作 */
.entries {
  display: flex;
  flex-direction: column;
  margin: var(--space4) calc(var(--space6) * -1) calc(var(--space5) * -1);
  border-top: 1px solid var(--panel-divider);
}

.entry {
  display: flex;
  align-items: center;
  gap: var(--space3);
  width: 100%;
  min-height: 64px;
  padding: var(--space3) var(--space6);
  border-top: 1px solid var(--panel-divider);
}

.entry:first-child {
  border-top: 0;
}

.entry:hover {
  background: color-mix(in srgb, var(--color-surface-secondary) 55%, transparent);
}

.entry__icon {
  flex: none;
  color: var(--color-text-secondary);
}

.entry__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.entry__title-row {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-width: 0;
}

.entry__title {
  flex: none;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
  line-height: 1.3;
}

.entry__desc {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.entry__value {
  flex: none;
  max-width: 28ch;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

/* 卡片内的入口：整行可点，去掉列表首行那种贴边样式 */
.entry--card {
  gap: var(--space3);
  padding: var(--space3) var(--space4);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--duration-micro), background var(--duration-micro);
}

.entry--card:hover {
  border-color: color-mix(in srgb, var(--color-primary) 45%, var(--panel-border));
  background: color-mix(in srgb, var(--color-surface-secondary) 60%, transparent);
}

.entry--card:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

.entry__caret {
  flex: none;
  color: var(--color-text-tertiary);
}

/* ---- MoviePilot 磁贴：大 logo 左置，右侧数据压紧 ---- */
.mp-tile {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  max-width: 300px;
  padding: 10px 12px;
  border: 1px solid color-mix(in srgb, #8b3fe8 14%, var(--panel-border));
  border-radius: var(--radius-xl);
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, #8b3fe8 7%, var(--color-surface)) 0%,
      var(--color-surface) 52%
    );
  box-shadow: var(--shadow-card);
  text-align: left;
  cursor: pointer;
  transition:
    border-color var(--duration-micro),
    background var(--duration-micro),
    box-shadow var(--duration-micro),
    transform var(--duration-micro);
}

.mp-tile:hover {
  border-color: color-mix(in srgb, #8b3fe8 40%, var(--panel-border));
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, #8b3fe8 11%, var(--color-surface)) 0%,
      var(--color-surface) 58%
    );
  box-shadow:
    var(--shadow-card),
    0 8px 20px color-mix(in srgb, #8b3fe8 10%, transparent);
  transform: translateY(-1px);
}

.mp-tile:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

.mp-tile__logo {
  position: relative;
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  border: 1px solid color-mix(in srgb, #8b3fe8 18%, transparent);
  background:
    radial-gradient(circle at 28% 22%, #efe4ff 0%, transparent 58%),
    linear-gradient(160deg, #f6f0ff 0%, #ebe0ff 100%);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.8);
}

.mp-tile__mark {
  display: block;
  width: 44px;
  height: 44px;
  object-fit: contain;
}

.mp-tile__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  line-height: 1.25;
}

.mp-tile__head {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
  margin-bottom: 1px;
}

.mp-tile__dot {
  position: absolute;
  top: -1px;
  right: -1px;
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  border: 2px solid var(--color-surface);
  background: var(--color-text-tertiary);
  box-sizing: border-box;
}

.mp-tile__dot.is-on {
  background: var(--color-success);
}

.mp-tile__dot.is-warn {
  background: var(--color-warning);
}

.mp-tile__dot.is-off {
  background: var(--color-danger);
}

.mp-tile__title {
  font-size: 13px;
  font-weight: var(--font-label-weight);
  letter-spacing: -0.01em;
  line-height: 18px;
  color: var(--color-text-primary);
  white-space: nowrap;
}

.mp-tile__badge {
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, #8b3fe8 12%, transparent);
  font-size: 10px;
  line-height: 15px;
  color: #7c3aed;
}

.mp-tile__remove {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  margin-left: auto;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition: background var(--duration-micro), color var(--duration-micro);
}

.mp-tile__remove:hover {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  color: var(--color-danger);
}

.mp-tile__row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 16px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.mp-tile__row--muted {
  font-size: 11px;
  line-height: 14px;
  color: var(--color-text-tertiary);
}

.mp-tile__metric {
  display: inline-flex;
  align-items: baseline;
  gap: 2px;
  font-variant-numeric: tabular-nums;
}

.mp-tile__metric-key {
  color: var(--color-text-tertiary);
}

.mp-tile__divider {
  flex: none;
  width: 1px;
  height: 9px;
  background: var(--panel-border);
}

.mp-meta__bad {
  color: var(--color-danger);
}

/* 未接入时的占位方块 */
.qb-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border: 1px dashed var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: border-color var(--duration-micro), color var(--duration-micro);
}

.qb-add:hover {
  border-color: color-mix(in srgb, var(--color-primary) 55%, var(--panel-border));
  color: var(--color-primary);
}

.qb-add:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

.chip {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 var(--space2);
  border-radius: var(--radius-full);
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  font-size: var(--font-caption-size);
  line-height: 1;
  white-space: nowrap;
}

.chip.is-off {
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.gh {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

/* 下载器弹窗：表单在上、试连结果与按钮贴底右对齐 */
.qb {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

.qb__ops {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space3);
  min-height: 32px;
}

.qb__msg {
  flex: 1;
  min-width: 0;
  font-size: var(--font-caption-size);
  line-height: 1.5;
  word-break: break-word;
}

.qb__msg.is-ok {
  color: var(--color-text-secondary);
}

.qb__msg.is-bad {
  color: var(--color-danger);
}

.gh__status {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space4);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  box-shadow: var(--shadow-card);
}

.gh__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
}

.gh__status.is-off {
  border-color: color-mix(in srgb, var(--color-danger) 32%, var(--panel-border));
}

.gh__status.is-off .gh__badge {
  color: var(--color-danger);
}

.gh__who {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.gh__login {
  display: flex;
  align-items: center;
  gap: var(--space2);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.gh__dot {
  width: 3px;
  height: 3px;
  border-radius: var(--radius-full);
  background: var(--color-text-tertiary);
}

.gh__source {
  font-weight: var(--font-caption-weight);
  color: var(--color-text-secondary);
}

.gh__meta {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
  overflow-wrap: anywhere;
}

.gh__ops {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: var(--space2);
  flex: none;
}

.gh__ops--start {
  justify-content: flex-start;
}

.gh__steps {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  margin: 0;
  padding: var(--space4) var(--space4) var(--space4) var(--space6);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  box-shadow: var(--shadow-card);
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.gh__link {
  color: var(--color-primary);
  text-decoration: underline;
  overflow-wrap: anywhere;
}

.gh__link:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}

.gh__code {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  padding: var(--space3) var(--space4);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.gh__code-value {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 20px;
  letter-spacing: 0.16em;
  color: var(--color-text-primary);
}

.gh__manual-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  padding-top: var(--space4);
  border-top: 1px solid var(--panel-divider);
}

.gh__manual-head {
  display: flex;
  flex-direction: column;
  gap: var(--space1);
}

.gh__manual-title {
  margin: 0;
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.gh__manual-hint {
  margin: 0;
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.gh__manual {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--space2);
  align-items: center;
}

.gh__manual-icon {
  flex: none;
  color: var(--color-text-tertiary);
}

.gh__note {
  margin: 0;
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.gh__status .chip {
  margin-left: auto;
  flex: none;
}

/* ---- 分段控件 */
.segmented {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.segmented--fill {
  display: flex;
  width: 100%;
}

.segmented--fill .segmented__item {
  flex: 1;
}

.segmented__item {
  height: 30px;
  padding: 0 var(--space3);
  border-radius: var(--radius-sm);
  font-size: var(--font-caption-size);
  line-height: 1;
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease,
    box-shadow var(--duration-micro) ease;
}

.segmented__item:hover:not(.is-active) {
  color: var(--color-text-primary);
}

.segmented__item.is-active {
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: var(--font-label-weight);
  box-shadow: var(--shadow-card);
}

.segmented__item:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}

/* ---- 高级配置弹窗：等宽 tab + 扁平行块（不套内卡） */
.sheet {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.sheet-tabs {
  display: flex;
  width: 100%;
  gap: var(--space1);
  padding: var(--space1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
}

.sheet-tabs__item {
  flex: 1;
  height: 32px;
  padding: 0 var(--space2);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
  transition:
    color var(--duration-micro) ease,
    background-color var(--duration-micro) ease,
    box-shadow var(--duration-micro) ease;
}

.sheet-tabs__item:hover {
  color: var(--color-text-primary);
}

.sheet-tabs__item.is-active {
  color: var(--color-text-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.sheet-tabs__item:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}

.sheet-panel {
  display: flex;
  flex-direction: column;
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
}

.sheet-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  min-height: 48px;
  padding: var(--space2) 0;
}

.sheet-row + .sheet-row {
  border-top: 1px solid var(--panel-divider);
}

.sheet-row--stack {
  align-items: stretch;
  flex-direction: column;
  justify-content: center;
  gap: var(--space2);
  min-height: 0;
  padding-top: var(--space3);
  padding-bottom: var(--space3);
}

.sheet-label {
  display: flex;
  flex-flow: row wrap;
  align-items: baseline;
  gap: var(--space2);
  min-width: 0;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
  line-height: 1.35;
}

.sheet-hint {
  font-size: var(--font-caption-size);
  font-weight: 400;
  color: var(--color-text-secondary);
  line-height: 1.35;
}

.sheet-input {
  width: 100%;
  height: 36px;
  padding: 0 var(--space3);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  box-shadow: inset 0 1px 0 var(--highlight-line);
  font: inherit;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.sheet-input:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}

.sheet-input:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.sheet-input--num {
  flex: none;
  width: 88px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.sheet-empty {
  margin: 0;
  font-size: var(--font-caption-size);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

/* 弹窗 teleport 到 body，不在 .sys 内，开关样式在此补一份 */
.switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex: none;
  cursor: pointer;
}

.switch input {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  cursor: pointer;
}

.switch__track {
  width: 40px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-separator);
  transition: background-color var(--duration-micro) ease;
}

.switch__track::after {
  content: '';
  display: block;
  width: 18px;
  height: 18px;
  margin: 2px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  transition: transform var(--duration-micro) ease;
}

.switch input:checked + .switch__track {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.switch input:checked + .switch__track::after {
  transform: translateX(16px);
}

.switch input:focus-visible + .switch__track {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

@media (max-width: 900px) {
  .entries {
    margin-left: calc(var(--space4) * -1);
    margin-right: calc(var(--space4) * -1);
  }

  .entry {
    padding: var(--space3) var(--space4);
  }

  .entry__value {
    display: none;
  }
}

@media (max-width: 720px) {
  .gh__manual {
    grid-template-columns: minmax(0, 1fr);
  }

  /* 窄屏状态卡改为上下排，令牌摘要才有整行宽度 */
  .gh__status {
    align-items: flex-start;
  }

  .gh__login {
    flex-wrap: wrap;
    row-gap: 2px;
  }

  .gh__code-value {
    font-size: 16px;
  }

  .field__head {
    flex-direction: column;
    gap: 2px;
  }

  .field__hint {
    white-space: normal;
  }
}
</style>
