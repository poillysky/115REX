<script setup lang="ts">
// 站点管理：卡片网格 + 筛选/导出/排序 + 完整编辑 + 连通测试（对齐 MoviePilot 站点页）。
import { computed, onMounted, reactive, ref } from 'vue'

import { useNotifyStore } from '@/application/notify'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'
import SiteCard from '@/features/system/SiteCard.vue'
import SiteImportDialog from '@/features/system/SiteImportDialog.vue'
import SiteStatisticsDialog from '@/features/system/SiteStatisticsDialog.vue'
import { describeError } from '@/core/api/error'
import { sitesApi } from '@/data/api'
import type {
  Site,
  SiteConnectionStatus,
  SiteStatistic,
  SiteWrite,
} from '@/domain/contract'

type FilterKey = 'all' | 'active' | 'inactive' | SiteConnectionStatus
type AuthTab = 'cookie' | 'api'

const FILTERS: { value: FilterKey; label: string }[] = [
  { value: 'all', label: '全部' },
  { value: 'active', label: '启用' },
  { value: 'inactive', label: '停用' },
  { value: 'connected', label: '连通正常' },
  { value: 'slow', label: '连通较慢' },
  { value: 'failed', label: '连通失败' },
  { value: 'unknown', label: '未测试' },
]

const notify = useNotifyStore()

const sites = ref<Site[]>([])
const statsMap = ref<Record<string, SiteStatistic>>({})
const loading = ref(true)
const errorText = ref('')

const filter = ref<FilterKey>('all')
const filterOpen = ref(false)
const sortMode = ref(false)
const savingPriority = ref(false)

const importOpen = ref(false)
const statisticsOpen = ref(false)

const editOpen = ref(false)
const editMode = ref<'create' | 'edit'>('create')
const editBusy = ref(false)
const editError = ref('')
const editId = ref<number | null>(null)
const authTab = ref<AuthTab>('cookie')
const limitEnabled = ref(false)
const form = reactive({
  name: '',
  domain: '',
  url: '',
  pri: 0,
  cookie: '',
  ua: '',
  rss: '',
  apikey: '',
  token: '',
  note: '',
  timeout: 15,
  proxy: false,
  render: false,
  public: false,
  isActive: true,
  filter: '',
  downloader: '',
  limitInterval: 0,
  limitCount: 0,
  limitSeconds: 0,
})

const deleteOpen = ref(false)
const deleteTarget = ref<Site | null>(null)
const deleteBusy = ref(false)
const deleteError = ref('')

const activeCount = computed(() => sites.value.filter((item) => item.isActive).length)

const currentFilterLabel = computed(
  () => FILTERS.find((item) => item.value === filter.value)?.label ?? '全部',
)

function connectionOf(domain: string): SiteConnectionStatus {
  const stats = statsMap.value[domain]
  if (!stats) return 'unknown'
  if (stats.lstState === 1) return 'failed'
  if (stats.lstState === 0) {
    if (!stats.seconds) return 'unknown'
    if (stats.seconds >= 5) return 'slow'
    return 'connected'
  }
  return 'unknown'
}

const filteredSites = computed(() => {
  if (filter.value === 'all') return sites.value
  return sites.value.filter((site) => {
    if (filter.value === 'active') return site.isActive
    if (filter.value === 'inactive') return !site.isActive
    return connectionOf(site.domain) === filter.value
  })
})

function blankForm(): void {
  form.name = ''
  form.domain = ''
  form.url = ''
  form.pri = 0
  form.cookie = ''
  form.ua = ''
  form.rss = ''
  form.apikey = ''
  form.token = ''
  form.note = ''
  form.timeout = 15
  form.proxy = false
  form.render = false
  form.public = false
  form.isActive = true
  form.filter = ''
  form.downloader = ''
  form.limitInterval = 0
  form.limitCount = 0
  form.limitSeconds = 0
  limitEnabled.value = false
  authTab.value = 'cookie'
}

function fillForm(site: Site): void {
  form.name = site.name
  form.domain = site.domain
  form.url = site.url
  form.pri = site.pri
  form.cookie = site.cookie
  form.ua = site.ua
  form.rss = site.rss
  form.apikey = site.apikey
  form.token = site.token
  form.note = site.note
  form.timeout = site.timeout
  form.proxy = site.proxy
  form.render = site.render
  form.public = site.public
  form.isActive = site.isActive
  form.filter = site.filter
  form.downloader = site.downloader
  form.limitInterval = site.limitInterval
  form.limitCount = site.limitCount
  form.limitSeconds = site.limitSeconds
  limitEnabled.value = Boolean(
    site.limitInterval || site.limitCount || site.limitSeconds,
  )
  authTab.value = site.apikey || site.token ? 'api' : 'cookie'
}

function toWrite(): SiteWrite {
  return {
    name: form.name.trim(),
    domain: form.domain.trim(),
    url: form.url.trim(),
    pri: Number(form.pri) || 0,
    rss: form.rss.trim(),
    cookie: form.cookie,
    apikey: form.apikey.trim(),
    token: form.token.trim(),
    ua: form.ua.trim(),
    proxy: form.proxy,
    filter: form.filter.trim(),
    render: form.render,
    public: form.public,
    note: form.note.trim(),
    timeout: Math.max(1, Number(form.timeout) || 15),
    downloader: form.downloader.trim(),
    limitInterval: limitEnabled.value ? Math.max(0, Number(form.limitInterval) || 0) : 0,
    limitCount: limitEnabled.value ? Math.max(0, Number(form.limitCount) || 0) : 0,
    limitSeconds: limitEnabled.value ? Math.max(0, Number(form.limitSeconds) || 0) : 0,
    isActive: form.isActive,
  }
}

async function loadStats(): Promise<void> {
  try {
    const res = await sitesApi.statistics()
    const next: Record<string, SiteStatistic> = {}
    for (const item of res.stats) {
      if (item.domain) next[item.domain] = item
    }
    statsMap.value = next
  } catch {
    statsMap.value = {}
  }
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [list] = await Promise.all([sitesApi.list(), loadStats()])
    sites.value = list.sites
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

function selectFilter(value: FilterKey): void {
  filter.value = value
  filterOpen.value = false
  if (value !== 'all' && sortMode.value) sortMode.value = false
}

function toggleSortMode(): void {
  if (filter.value !== 'all') {
    notify.failure('排序请先切换到「全部」筛选')
    return
  }
  sortMode.value = !sortMode.value
}

function openCreate(): void {
  editMode.value = 'create'
  editId.value = null
  editError.value = ''
  blankForm()
  editOpen.value = true
}

function openEdit(site: Site): void {
  editMode.value = 'edit'
  editId.value = site.id
  editError.value = ''
  fillForm(site)
  editOpen.value = true
}

async function autoFillName(): Promise<void> {
  const url = form.url.trim()
  if (!url || form.domain) return
  // 名称已有值（编辑态或用户手填）时不覆盖
  if (form.name.trim()) return
  try {
    const meta = await sitesApi.meta(url, form.ua, form.proxy)
    if (meta.name) form.name = meta.name
    form.domain = meta.domain
  } catch {
    // 抓不到标题就交给后端按域名回落，这里保持静默
  }
}

async function submitEdit(): Promise<void> {
  const payload = toWrite()
  if (!payload.url) {
    editError.value = '请填写站点地址'
    return
  }
  editBusy.value = true
  editError.value = ''
  try {
    if (editMode.value === 'create') {
      await sitesApi.create(payload)
      notify.success('已添加站点')
    } else if (editId.value != null) {
      await sitesApi.update(editId.value, payload)
      notify.success('已保存站点')
    }
    editOpen.value = false
    await load()
  } catch (error) {
    editError.value = describeError(error)
  } finally {
    editBusy.value = false
  }
}

async function toggleActive(site: Site, next: boolean): Promise<void> {
  try {
    await sitesApi.patch(site.id, { isActive: next })
    site.isActive = next
  } catch (error) {
    notify.failure(describeError(error))
  }
}

function askDelete(site: Site): void {
  deleteTarget.value = site
  deleteError.value = ''
  deleteOpen.value = true
}

async function submitDelete(): Promise<void> {
  const target = deleteTarget.value
  if (!target) return
  deleteBusy.value = true
  deleteError.value = ''
  try {
    await sitesApi.remove(target.id)
    deleteOpen.value = false
    deleteTarget.value = null
    notify.success('已删除站点')
    await load()
  } catch (error) {
    deleteError.value = describeError(error)
  } finally {
    deleteBusy.value = false
  }
}

async function persistPriorities(ordered: Site[]): Promise<void> {
  if (savingPriority.value) return
  savingPriority.value = true
  const snapshot = sites.value
  sites.value = ordered
  try {
    const items = ordered.map((site, index) => ({ id: site.id, pri: index + 1 }))
    const res = await sitesApi.updatePriorities(items)
    sites.value = res.sites
  } catch (error) {
    sites.value = snapshot
    notify.failure(describeError(error))
  } finally {
    savingPriority.value = false
  }
}

async function moveSite(site: Site, delta: -1 | 1): Promise<void> {
  const list = [...sites.value]
  const index = list.findIndex((item) => item.id === site.id)
  const next = index + delta
  if (index < 0 || next < 0 || next >= list.length) return
  const [item] = list.splice(index, 1)
  list.splice(next, 0, item)
  await persistPriorities(list)
}

function onStatsUpdated(stat: SiteStatistic): void {
  statsMap.value = { ...statsMap.value, [stat.domain]: stat }
}

function exportSites(): void {
  if (!sites.value.length) {
    notify.failure('暂无站点可导出')
    return
  }
  const exportData = sites.value.map((site) => ({
    name: site.name,
    domain: site.domain,
    url: site.url,
    rss: site.rss,
    downloader: site.downloader,
    cookie: site.cookie,
    apikey: site.apikey,
    token: site.token,
    ua: site.ua,
    proxy: site.proxy,
    filter: site.filter,
    render: site.render,
    public: site.public,
    note: site.note,
    timeout: site.timeout,
    limit_interval: site.limitInterval,
    limit_count: site.limitCount,
    limit_seconds: site.limitSeconds,
    is_active: site.isActive,
    pri: site.pri,
  }))
  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `sites_export_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  notify.success('已导出站点 JSON')
}

onMounted(() => {
  void load()
})
</script>

<template>
  <SysStyles>
    <div class="sites">
      <header class="sites__toolbar">
        <div class="sites__actions">
          <AppButton variant="primary" size="sm" @click="openCreate">添加站点</AppButton>
          <AppButton size="sm" @click="importOpen = true">导入</AppButton>
          <AppButton size="sm" :disabled="!sites.length" @click="exportSites">导出</AppButton>
          <AppButton size="sm" :disabled="!sites.length" @click="statisticsOpen = true">
            统计
          </AppButton>
          <div class="sites__filter">
            <button
              type="button"
              class="sites__icon-btn"
              :class="{ 'is-active': filter !== 'all' }"
              :title="`筛选：${currentFilterLabel}`"
              aria-haspopup="listbox"
              :aria-expanded="filterOpen"
              @click="filterOpen = !filterOpen"
            >
              <AppIcon name="list" :size="16" />
            </button>
            <div v-if="filterOpen" class="sites__filter-menu" role="listbox">
              <button
                v-for="item in FILTERS"
                :key="item.value"
                type="button"
                role="option"
                :aria-selected="filter === item.value"
                class="sites__filter-item"
                :class="{ 'is-selected': filter === item.value }"
                @click="selectFilter(item.value)"
              >
                {{ item.label }}
                <AppIcon v-if="filter === item.value" name="check" :size="14" />
              </button>
            </div>
          </div>
          <button
            type="button"
            class="sites__icon-btn"
            :class="{ 'is-active': sortMode }"
            title="排序"
            aria-label="排序"
            @click="toggleSortMode"
          >
            <AppIcon name="layers" :size="16" />
          </button>
          <button
            type="button"
            class="sites__icon-btn"
            title="刷新"
            aria-label="刷新"
            :disabled="loading"
            @click="void load()"
          >
            <AppIcon name="refresh" :size="16" />
          </button>
        </div>
        <p v-if="sites.length" class="sites__summary tabular">
          共 {{ sites.length }} 个 · 启用 {{ activeCount }}
          <template v-if="filter !== 'all'"> · {{ currentFilterLabel }} {{ filteredSites.length }}</template>
        </p>
      </header>

      <div v-if="sortMode" class="sites__sort-hint">
        <span>排序模式：用卡片上的箭头调整优先级，数值越小越靠前。</span>
        <AppButton size="sm" @click="sortMode = false">退出</AppButton>
      </div>

      <AppErrorState v-if="errorText" :message="errorText" @retry="() => load()" />

      <div v-else-if="loading && !sites.length" class="sites__skel">
        <AppSkeleton v-for="n in 6" :key="n" height="148px" />
      </div>

      <AppEmptyState
        v-else-if="!loading && !sites.length"
        title="还没有站点"
        description="可手动添加，或导入 MoviePilot 导出的站点 JSON。"
        icon="compass"
      >
        <div class="sites__empty-actions">
          <AppButton variant="primary" size="sm" @click="openCreate">添加站点</AppButton>
          <AppButton size="sm" @click="importOpen = true">导入 JSON</AppButton>
        </div>
      </AppEmptyState>

      <AppEmptyState
        v-else-if="!filteredSites.length"
        title="没有匹配的站点"
        description="试试换一个筛选条件。"
        icon="search"
      >
        <AppButton size="sm" @click="selectFilter('all')">显示全部</AppButton>
      </AppEmptyState>

      <section v-else class="sites__grid">
        <SiteCard
          v-for="site in filteredSites"
          :key="site.id"
          :site="site"
          :stats="statsMap[site.domain]"
          :sortable="sortMode && filter === 'all'"
          @edit="openEdit(site)"
          @remove="askDelete(site)"
          @toggle-active="(next) => void toggleActive(site, next)"
          @stats-updated="onStatsUpdated"
          @move-up="void moveSite(site, -1)"
          @move-down="void moveSite(site, 1)"
        />
      </section>
    </div>

    <SiteImportDialog v-model:open="importOpen" @success="void load()" />

    <SiteStatisticsDialog
      v-model:open="statisticsOpen"
      :sites="sites"
      @refresh="void loadStats()"
    />

    <AppDialog
      v-model:open="editOpen"
      :title="editMode === 'create' ? '添加站点' : '编辑站点'"
      size="xl"
    >
      <div class="edit">
        <section class="edit__block">
          <div class="edit__grid edit__grid--3">
            <label class="field">
              <span class="field__label">站点地址</span>
              <input
                v-model="form.url"
                class="field__input"
                placeholder="https://www.example.com/"
                autocomplete="off"
                @blur="autoFillName"
              />
              <span class="field__hint">格式：https://www.example.com/</span>
            </label>
            <label class="field">
              <span class="field__label">优先级</span>
              <input v-model.number="form.pri" class="field__input" type="number" min="0" />
              <span class="field__hint">优先级越小越优先</span>
            </label>
            <label class="field">
              <span class="field__label">状态</span>
              <span class="field__switch-row">
                <span class="switch">
                  <input v-model="form.isActive" type="checkbox" aria-label="启用站点" />
                  <span class="switch__track" aria-hidden="true" />
                </span>
                <span class="field__switch-text">{{ form.isActive ? '启用' : '停用' }}</span>
              </span>
              <span class="field__hint">停用后不参与聚合搜索</span>
            </label>
            <label class="field">
              <span class="field__label">RSS 地址</span>
              <input
                v-model="form.rss"
                class="field__input"
                placeholder="https://www.example.com/rss"
                autocomplete="off"
              />
              <span class="field__hint">订阅模式下使用的订阅链接，未自动获取需手动补充</span>
            </label>
            <label class="field">
              <span class="field__label">超时时间（秒）</span>
              <input v-model.number="form.timeout" class="field__input" type="number" min="0" />
              <span class="field__hint">超时时间，为 0 时不限制</span>
            </label>
            <label class="field">
              <span class="field__label">下载器</span>
              <select v-model="form.downloader" class="field__select">
                <option value="">默认</option>
              </select>
              <span class="field__hint">此站点使用的下载器</span>
            </label>
          </div>
        </section>

        <section class="edit__block">
          <div class="edit__head">
            <h3 class="edit__title">认证</h3>
            <div class="edit__tabs" role="tablist">
          <button
            type="button"
            role="tab"
            class="edit__tab"
            :class="{ 'is-active': authTab === 'cookie' }"
            :aria-selected="authTab === 'cookie'"
            @click="authTab = 'cookie'"
          >
            <AppIcon name="key" :size="14" aria-hidden="true" />
            Cookie
          </button>
          <button
            type="button"
            role="tab"
            class="edit__tab"
            :class="{ 'is-active': authTab === 'api' }"
            :aria-selected="authTab === 'api'"
            @click="authTab = 'api'"
          >
            <AppIcon name="link" :size="14" aria-hidden="true" />
            API
          </button>
            </div>
          </div>

          <label v-if="authTab === 'cookie'" class="field">
            <textarea
              v-model="form.cookie"
              class="field__textarea field__textarea--tall"
              placeholder="站点 Cookie"
              rows="5"
            />
            <span class="field__hint">站点请求头中的 Cookie 信息</span>
          </label>
          <div v-else class="edit__grid">
            <label class="field">
              <span class="field__label">Authorization</span>
              <input v-model="form.token" class="field__input" autocomplete="off" />
            </label>
            <label class="field">
              <span class="field__label">API Key</span>
              <input v-model="form.apikey" class="field__input" autocomplete="off" />
            </label>
          </div>

          <label v-if="authTab === 'cookie'" class="field">
            <span class="field__label">User-Agent</span>
            <input
              v-model="form.ua"
              class="field__input"
              placeholder="站点 User-Agent"
              autocomplete="off"
            />
            <span class="field__hint">获取 Cookie 的浏览器对应的 User-Agent</span>
          </label>
        </section>

        <section class="edit__block edit__block--last">
          <h3 class="edit__title">访问控制</h3>
          <div class="edit__grid edit__grid--3">
            <label class="edit__switch">
              <span class="switch">
                <input v-model="limitEnabled" type="checkbox" aria-label="限制站点访问频率" />
                <span class="switch__track" aria-hidden="true" />
              </span>
              <span class="edit__switch-text">
                <span class="edit__switch-title">限制站点访问频率</span>
                <span class="edit__switch-desc">按单位时间放行，避免触发站点风控</span>
              </span>
            </label>
            <label class="edit__switch">
              <span class="switch">
                <input v-model="form.proxy" type="checkbox" aria-label="使用代理访问" />
                <span class="switch__track" aria-hidden="true" />
              </span>
              <span class="edit__switch-text">
                <span class="edit__switch-title">使用代理访问</span>
                <span class="edit__switch-desc">使用代理服务器访问该站点</span>
              </span>
            </label>
            <label class="edit__switch">
              <span class="switch">
                <input v-model="form.render" type="checkbox" aria-label="浏览器仿真" />
                <span class="switch__track" aria-hidden="true" />
              </span>
              <span class="edit__switch-text">
                <span class="edit__switch-title">浏览器仿真</span>
                <span class="edit__switch-desc">使用浏览器模拟真实访问该站点</span>
              </span>
            </label>
          </div>
          <div v-if="limitEnabled" class="edit__grid edit__grid--3 edit__switches-params">
            <label class="field">
              <span class="field__label">单位时间（秒）</span>
              <input
                v-model.number="form.limitInterval"
                class="field__input"
                type="number"
                min="0"
              />
            </label>
            <label class="field">
              <span class="field__label">单位时间内次数</span>
              <input
                v-model.number="form.limitCount"
                class="field__input"
                type="number"
                min="0"
              />
            </label>
            <label class="field">
              <span class="field__label">访问间隔（秒）</span>
              <input
                v-model.number="form.limitSeconds"
                class="field__input"
                type="number"
                min="0"
              />
            </label>
          </div>
        </section>

        <p v-if="editError" class="edit__error">{{ editError }}</p>
      </div>
      <template #footer>
        <AppButton size="sm" @click="editOpen = false">取消</AppButton>
        <AppButton size="sm" variant="primary" :loading="editBusy" @click="submitEdit">
          {{ editMode === 'create' ? '添加' : '保存' }}
        </AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="deleteOpen"
      title="删除站点？"
      :description="deleteTarget ? `将删除「${deleteTarget.name}」` : ''"
      tone="danger"
      size="sm"
    >
      <p v-if="deleteError" class="field__hint field__hint--error">{{ deleteError }}</p>
      <template #footer>
        <AppButton size="sm" @click="deleteOpen = false">取消</AppButton>
        <AppButton size="sm" variant="danger" :loading="deleteBusy" @click="submitDelete">
          确认删除
        </AppButton>
      </template>
    </AppDialog>
  </SysStyles>
</template>

<style scoped>
.sites {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.sites__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  flex-wrap: wrap;
}

.sites__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space2);
  flex-wrap: wrap;
}

.sites__filter {
  position: relative;
}

.sites__filter-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 20;
  min-width: 148px;
  padding: 4px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.sites__filter-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  text-align: left;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
  cursor: pointer;
}

.sites__filter-item:hover,
.sites__filter-item.is-selected {
  background: var(--color-surface-secondary);
}

.sites__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.sites__icon-btn:hover:not(:disabled),
.sites__icon-btn.is-active {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.sites__icon-btn.is-active {
  color: var(--color-primary);
}

.sites__icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.sites__summary {
  margin: 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.sites__sort-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  padding: var(--space2) var(--space3);
  border-radius: var(--radius-md);
  border: 1px solid color-mix(in srgb, var(--color-warning, #d97706) 35%, var(--panel-border));
  background: color-mix(in srgb, var(--color-warning, #d97706) 8%, var(--color-surface));
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.sites__skel {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space3);
}

.sites__empty-actions {
  display: inline-flex;
  gap: var(--space2);
}

.sites__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space3);
}

/* 表单按字段自上而下排列，靠行间距分节，不加内层卡片 */
.edit {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

/* 分节：细分隔线 + 留白拉开层级，不套卡片 */
.edit__block {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  padding-bottom: var(--space4);
  border-bottom: 1px solid var(--panel-divider);
}

.edit__block--last {
  padding-bottom: 0;
  border-bottom: 0;
}

.edit__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
}

.edit__title {
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  letter-spacing: 0.02em;
  color: var(--color-text-secondary);
}

.edit__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space4) var(--space4);
}

.edit__grid--3 {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

/* 状态字段：拨杆与文字同一行，占位高度与选择框一致 */
.field__switch-row {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-height: 38px;
}

.field__switch-text {
  font-size: var(--font-body-size);
  color: var(--color-text-primary);
}

.edit__tabs {
  display: inline-flex;
  align-self: flex-start;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-text-tertiary) 12%, transparent);
}

.edit__tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: 0;
  border-radius: 5px;
  background: transparent;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.edit__tab:hover {
  color: var(--color-text-primary);
}

.edit__tab.is-active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: var(--shadow-card);
}

/* 三个开关并排一行，拨杆在标题前面 */
.edit__switch {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-width: 0;
  cursor: pointer;
}

.edit__switch-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.edit__switch-title {
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.edit__switch-desc {
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-tertiary);
}

/* 代理与仿真两项的说明写在标题下方，和上面单行开关区分开 */
.edit__switch--stacked {
  align-items: flex-start;
}

.edit__switch--stacked .switch {
  margin-top: 1px;
}

.edit__switches-params {
  padding-left: var(--space3);
  border-left: 2px solid var(--panel-divider);
}

/* 说明文字换行时，拨杆对齐到标题那一行 */
.edit__grid--3 > .edit__switch {
  align-items: flex-start;
}

.edit__grid--3 > .edit__switch .switch {
  margin-top: 1px;
}

.edit__switch .switch {
  flex: none;
}

/* 开关样式随弹窗 teleport 到 body，需在本组件补一份 */
.switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  flex: none;
  cursor: pointer;
}

.switch input {
  position: absolute;
  width: 100%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.switch__track {
  width: 40px;
  height: 24px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-separator);
  background: var(--color-surface-secondary);
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

/* Cookie 是唯一的多行输入，给足高度方便整段粘贴 */
.field__textarea--tall {
  min-height: 132px;
  resize: vertical;
}

.edit__error {
  padding: var(--space2) var(--space3);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-danger) 10%, transparent); /* taste-skill-ignore：错误提示底色 */
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.tabular {
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .edit__grid,
  .edit__grid--3 {
    grid-template-columns: minmax(0, 1fr);
  }

  .sites__sort-hint {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
