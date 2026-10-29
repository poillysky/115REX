<script setup lang="ts">
// 站点统计：概览数字 + 按连通状态排序的列表 + 单站点耗时详情
// （对齐 MoviePilot SiteStatisticsDialog）。
// 状态判定与站点列表一致：失败 → 失败；秒数为 0 → 未测试；>= 5s → 较慢；其余正常。
import { computed, ref, watch } from 'vue'

import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import { describeError } from '@/core/api/error'
import { sitesApi } from '@/data/api'
import type { Site, SiteConnectionStatus, SiteStatistic } from '@/domain/contract'

const props = defineProps<{
  sites: Site[]
}>()

const open = defineModel<boolean>('open', { required: true })

const emit = defineEmits<{ refresh: [] }>()

const loading = ref(false)
const errorText = ref('')
const statsMap = ref<Record<string, SiteStatistic>>({})

const detailOpen = ref(false)
const detailSite = ref<Site | null>(null)
const detailStats = ref<SiteStatistic | null>(null)
const detailLoading = ref(false)
const detailError = ref('')

interface StatRow {
  site: Site
  stats: SiteStatistic | null
  status: SiteConnectionStatus
}

const STATUS_LABEL: Record<SiteConnectionStatus, string> = {
  connected: '正常',
  slow: '较慢',
  failed: '失败',
  unknown: '未测试',
}

const STATUS_TONE: Record<SiteConnectionStatus, 'success' | 'warning' | 'danger' | 'neutral'> = {
  connected: 'success',
  slow: 'warning',
  failed: 'danger',
  unknown: 'neutral',
}

/** 排序权重：正常 → 较慢 → 失败 → 未测试 */
const STATUS_ORDER: Record<SiteConnectionStatus, number> = {
  connected: 0,
  slow: 1,
  failed: 2,
  unknown: 3,
}

function statusOf(stats: SiteStatistic | null): SiteConnectionStatus {
  if (!stats) return 'unknown'
  if (stats.lstState === 1) return 'failed'
  if (stats.lstState === 0) {
    if (!stats.seconds) return 'unknown'
    if (stats.seconds >= 5) return 'slow'
    return 'connected'
  }
  return 'unknown'
}

function successRate(stats: SiteStatistic | null): number | null {
  if (!stats) return null
  const total = (stats.success || 0) + (stats.fail || 0)
  if (!total) return null
  return Math.round((stats.success / total) * 100)
}

function timeColor(seconds: number): 'success' | 'warning' | 'danger' {
  if (seconds < 2) return 'success'
  if (seconds < 5) return 'warning'
  return 'danger'
}

const rows = computed<StatRow[]>(() =>
  props.sites
    .map((site) => {
      const stats = statsMap.value[site.domain] ?? null
      return { site, stats, status: statusOf(stats) }
    })
    .sort((a, b) => {
      const diff = STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      if (diff !== 0) return diff
      const sa = a.stats?.seconds ?? Number.MAX_SAFE_INTEGER
      const sb = b.stats?.seconds ?? Number.MAX_SAFE_INTEGER
      if (sa !== sb) return sa - sb
      return a.site.name.localeCompare(b.site.name, 'zh-Hans-CN')
    }),
)

const overview = computed(() => {
  const counts = { total: rows.value.length, connected: 0, slow: 0, failed: 0, unknown: 0 }
  for (const row of rows.value) counts[row.status] += 1
  return counts
})

/** 解析耗时记录 JSON：{"YYYY-MM-DD HH:MM:SS": 秒}，倒序取最近 10 条 */
const detailRecords = computed<{ time: string; seconds: number }[]>(() => {
  const note = detailStats.value?.note ?? ''
  if (!note) return []
  try {
    const data = JSON.parse(note) as unknown
    if (!data || typeof data !== 'object' || Array.isArray(data)) return []
    return Object.entries(data as Record<string, unknown>)
      .map(([time, value]) => ({ time, seconds: Number(value) || 0 }))
      .sort((a, b) => b.time.localeCompare(a.time))
      .slice(0, 10)
  } catch {
    return []
  }
})

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const res = await sitesApi.statistics()
    const next: Record<string, SiteStatistic> = {}
    for (const item of res.stats) {
      if (item.domain) next[item.domain] = item
    }
    statsMap.value = next
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

function openDetail(site: Site): void {
  detailSite.value = site
  detailStats.value = statsMap.value[site.domain] ?? null
  detailError.value = ''
  detailOpen.value = true
  void loadDetail(site.domain)
}

async function loadDetail(domain: string): Promise<void> {
  detailLoading.value = true
  detailError.value = ''
  try {
    detailStats.value = await sitesApi.statisticByDomain(domain)
  } catch (error) {
    detailError.value = describeError(error)
  } finally {
    detailLoading.value = false
  }
}

function close(): void {
  open.value = false
  detailOpen.value = false
  emit('refresh')
}

watch(
  open,
  (value) => {
    if (!value) return
    detailOpen.value = false
    void load()
  },
  { immediate: true },
)
</script>

<template>
  <AppDialog :open="open" title="站点统计" size="lg" @update:open="open = $event">
    <div class="stat">
      <div class="stat__overview">
        <div class="stat__metric">
          <span class="stat__metric-value tabular">{{ overview.total }}</span>
          <span class="stat__metric-label">总站点</span>
        </div>
        <div class="stat__metric">
          <span class="stat__metric-value tabular stat__metric-value--success">
            {{ overview.connected }}
          </span>
          <span class="stat__metric-label">正常</span>
        </div>
        <div class="stat__metric">
          <span class="stat__metric-value tabular stat__metric-value--warning">
            {{ overview.slow }}
          </span>
          <span class="stat__metric-label">较慢</span>
        </div>
        <div class="stat__metric">
          <span class="stat__metric-value tabular stat__metric-value--danger">
            {{ overview.failed }}
          </span>
          <span class="stat__metric-label">失败</span>
        </div>
        <div class="stat__metric">
          <span class="stat__metric-value tabular">{{ overview.unknown }}</span>
          <span class="stat__metric-label">未测试</span>
        </div>
      </div>

      <p v-if="errorText" class="stat__error">{{ errorText }}</p>

      <AppEmptyState
        v-else-if="loading && !rows.length"
        title="正在读取统计"
        description="请稍候。"
        icon="clock"
      />

      <AppEmptyState
        v-else-if="!rows.length"
        title="还没有站点"
        description="添加站点并测试连通后，这里会汇总耗时与成功率。"
        icon="compass"
      />

      <ul v-else class="stat__list">
        <li v-for="row in rows" :key="row.site.id" class="stat__row">
          <span
            class="stat__dot"
            :class="`stat__dot--${STATUS_TONE[row.status]}`"
            aria-hidden="true"
          />
          <div class="stat__main">
            <div class="stat__title-line">
              <span class="stat__name" :title="row.site.name">{{ row.site.name }}</span>
              <AppBadge :tone="STATUS_TONE[row.status]">{{ STATUS_LABEL[row.status] }}</AppBadge>
            </div>
            <span class="stat__domain">{{ row.site.domain }}</span>
          </div>
          <div class="stat__cell">
            <span class="stat__cell-label">平均耗时</span>
            <span v-if="row.stats && row.stats.seconds" class="stat__cell-value tabular">
              <span :class="`stat__time--${timeColor(row.stats.seconds)}`">
                {{ row.stats.seconds }}s
              </span>
            </span>
            <span v-else class="stat__cell-value stat__cell-value--muted">—</span>
          </div>
          <div class="stat__cell">
            <span class="stat__cell-label">成功率</span>
            <span
              v-if="successRate(row.stats) !== null"
              class="stat__cell-value tabular"
            >
              {{ successRate(row.stats) }}%
            </span>
            <span v-else class="stat__cell-value stat__cell-value--muted">—</span>
          </div>
          <AppButton size="sm" variant="secondary" @click="openDetail(row.site)">详情</AppButton>
        </li>
      </ul>
    </div>

    <template #footer>
      <AppButton size="sm" :loading="loading" @click="void load()">刷新</AppButton>
      <AppButton size="sm" variant="primary" @click="close">关闭</AppButton>
    </template>
  </AppDialog>

  <AppDialog v-model:open="detailOpen" :title="detailSite ? `${detailSite.name} 统计` : '站点统计'" size="md">
    <div class="detail">
      <p v-if="detailError" class="stat__error">{{ detailError }}</p>
      <template v-else>
        <div class="detail__grid">
          <div class="stat__metric">
            <span class="stat__metric-value tabular">{{ detailStats?.success ?? 0 }}</span>
            <span class="stat__metric-label">成功次数</span>
          </div>
          <div class="stat__metric">
            <span class="stat__metric-value tabular">{{ detailStats?.fail ?? 0 }}</span>
            <span class="stat__metric-label">失败次数</span>
          </div>
          <div class="stat__metric">
            <span class="stat__metric-value tabular">
              {{ detailStats && detailStats.seconds ? `${detailStats.seconds}s` : '—' }}
            </span>
            <span class="stat__metric-label">平均耗时</span>
          </div>
        </div>

        <div class="detail__row">
          <span class="detail__label">最后访问</span>
          <span class="detail__value tabular">
            {{ detailStats?.lstModDate || '—' }}
          </span>
        </div>

        <div class="detail__section">
          <span class="detail__label">最近耗时记录</span>
          <p v-if="detailLoading" class="detail__hint">读取中…</p>
          <p v-else-if="!detailRecords.length" class="detail__hint">暂无耗时记录</p>
          <ul v-else class="detail__records">
            <li v-for="item in detailRecords" :key="item.time" class="detail__record">
              <span class="detail__record-time tabular">{{ item.time }}</span>
              <span class="detail__record-value tabular" :class="`stat__time--${timeColor(item.seconds)}`">
                {{ item.seconds }}s
              </span>
            </li>
          </ul>
        </div>
      </template>
    </div>
    <template #footer>
      <AppButton size="sm" @click="detailOpen = false">关闭</AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

.stat__overview {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space2);
}

.stat__metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--space3);
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
}

.stat__metric-value {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  color: var(--color-text-primary);
  line-height: 1.2;
}

.stat__metric-value--success {
  color: var(--color-success);
}

.stat__metric-value--warning {
  color: var(--color-warning);
}

.stat__metric-value--danger {
  color: var(--color-danger);
}

.stat__metric-label {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.stat__error {
  margin: 0;
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.stat__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  overflow: hidden;
}

.stat__row {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: 10px 12px;
}

.stat__row + .stat__row {
  border-top: 1px solid var(--panel-divider);
}

.stat__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-text-tertiary);
}

.stat__dot--success {
  background: var(--color-success);
}

.stat__dot--warning {
  background: var(--color-warning);
}

.stat__dot--danger {
  background: var(--color-danger);
}

.stat__main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.stat__title-line {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-width: 0;
}

.stat__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.stat__domain {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.stat__cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 72px;
  text-align: right;
}

.stat__cell-label {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.stat__cell-value {
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.stat__cell-value--muted {
  color: var(--color-text-tertiary);
}

.stat__time--success {
  color: var(--color-success);
}

.stat__time--warning {
  color: var(--color-warning);
}

.stat__time--danger {
  color: var(--color-danger);
}

.detail {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.detail__grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space2);
}

.detail__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  font-size: var(--font-caption-size);
}

.detail__label {
  color: var(--color-text-secondary);
}

.detail__value {
  color: var(--color-text-primary);
}

.detail__section {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
}

.detail__hint {
  margin: 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.detail__records {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.detail__record {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  padding: 6px 10px;
  font-size: var(--font-caption-size);
}

.detail__record + .detail__record {
  border-top: 1px solid var(--panel-divider);
}

.detail__record-time {
  color: var(--color-text-secondary);
}

.detail__record-value {
  font-weight: var(--font-label-weight);
}

.tabular {
  font-variant-numeric: tabular-nums;
}

@media (max-width: 640px) {
  .stat__overview {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat__row {
    flex-wrap: wrap;
  }

  .stat__cell {
    min-width: 60px;
  }
}
</style>
