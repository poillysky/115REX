<script setup lang="ts">
// 站点卡片：连通状态、测速、启停、编辑/删除（对齐 MoviePilot SiteCard 核心交互）。
import { computed, ref } from 'vue'

import { useNotifyStore } from '@/application/notify'
import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import { describeError } from '@/core/api/error'
import { sitesApi } from '@/data/api'
import type {
  Site,
  SiteConnectionStatus,
  SiteProbeResult,
  SiteProbeSample,
  SiteStatistic,
} from '@/domain/contract'

const props = defineProps<{
  site: Site
  stats?: SiteStatistic | null
  sortable?: boolean
}>()

const emit = defineEmits<{
  edit: []
  remove: []
  'stats-updated': [stat: SiteStatistic]
  'toggle-active': [next: boolean]
  'move-up': []
  'move-down': []
}>()

const notify = useNotifyStore()
const testing = ref(false)
const menuOpen = ref(false)
const probing = ref(false)
const probeOpen = ref(false)
const probeResult = ref<SiteProbeResult | null>(null)

const connectionStatus = computed<SiteConnectionStatus>(() => {
  const stats = props.stats
  if (!stats) return 'unknown'
  if (stats.lstState === 1) return 'failed'
  if (stats.lstState === 0) {
    if (!stats.seconds) return 'unknown'
    if (stats.seconds >= 5) return 'slow'
    return 'connected'
  }
  return 'unknown'
})

const statusTone = computed(() => {
  switch (connectionStatus.value) {
    case 'connected':
      return 'success'
    case 'slow':
      return 'warning'
    case 'failed':
      return 'danger'
    default:
      return 'neutral'
  }
})

const statusLabel = computed(() => {
  switch (connectionStatus.value) {
    case 'connected':
      return props.stats ? `${props.stats.seconds}s` : '正常'
    case 'slow':
      return props.stats ? `${props.stats.seconds}s 较慢` : '较慢'
    case 'failed':
      return '失败'
    default:
      return '未测'
  }
})

async function testConnectivity(): Promise<void> {
  if (testing.value || props.sortable) return
  testing.value = true
  try {
    const result = await sitesApi.test(props.site.id)
    emit('stats-updated', result.statistic)
    if (result.ok) {
      notify.success(`${props.site.name} 连通正常（${result.seconds}s）`)
    } else {
      notify.failure(`${props.site.name}：${result.message || '连通失败'}`)
    }
  } catch (error) {
    notify.failure(describeError(error))
  } finally {
    testing.value = false
  }
}

function openUrl(): void {
  if (props.sortable || !props.site.url) return
  window.open(props.site.url, '_blank', 'noopener,noreferrer')
}

/** 用默认关键词试搜一次，确认搜索页能解析出种子；结果在弹窗展示，不落库。 */
async function probeSearch(): Promise<void> {
  if (probing.value || props.sortable) return
  probeOpen.value = true
  probing.value = true
  probeResult.value = null
  try {
    probeResult.value = await sitesApi.probe(props.site.id, '1080p')
  } catch (error) {
    probeResult.value = {
      ok: false,
      message: describeError(error),
      seconds: 0,
      url: props.site.url,
      matched: 0,
      samples: [],
    }
  } finally {
    probing.value = false
  }
}

function formatSize(bytes: number | null): string {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index >= 3 ? 2 : 0)} ${units[index]}`
}

function formatCategory(category: string | null): string {
  // 后端给的是 torrents.php?cat=N，列表里只留末尾的 cat 值
  if (!category) return '—'
  const match = /cat=(\d+)/.exec(category)
  return match ? `cat ${match[1]}` : category
}

function formatUntil(value: string): string {
  // 后端给的是 `2026-10-29 08:55:32`，列表里只保留到分钟
  return value.slice(5, 16)
}

type ProbeTagTone = 'promo' | 'warn' | 'info' | 'accent'

interface ProbeTag {
  label: string
  tone: ProbeTagTone
}

// 促销 / H&R / 置顶由后端按图标解析，标题里的语种角标仍从标题认
const TITLE_TAGS: Array<{ pattern: RegExp; label: string; tone: ProbeTagTone }> = [
  { pattern: /官方/i, label: '官方', tone: 'info' },
  { pattern: /国语/i, label: '国语', tone: 'accent' },
  { pattern: /中字|中文字幕/i, label: '中字', tone: 'accent' },
]

function sampleTags(sample: SiteProbeSample): ProbeTag[] {
  const tags: ProbeTag[] = []
  if (sample.sticky) tags.push({ label: '置顶', tone: 'info' })
  if (sample.promo) tags.push({ label: sample.promo, tone: 'promo' })
  if (sample.hitAndRun) tags.push({ label: 'H&R', tone: 'warn' })
  for (const item of TITLE_TAGS) {
    if (item.pattern.test(sample.title)) tags.push({ label: item.label, tone: item.tone })
  }
  return tags
}

function onCardClick(): void {
  if (props.sortable) return
  emit('edit')
}
</script>

<template>
  <article
    class="scard"
    :class="{
      'scard--inactive': !site.isActive,
      'scard--sortable': sortable,
      [`scard--${statusTone}`]: site.isActive,
    }"
    @click="onCardClick"
  >
    <div class="scard__bar" aria-hidden="true" />

    <header class="scard__head">
      <div class="scard__icon" aria-hidden="true">
        <AppIcon name="globe" :size="18" />
      </div>
      <div class="scard__title-wrap">
        <div class="scard__title-row">
          <h3 class="scard__title" :title="site.name">{{ site.name }}</h3>
          <AppBadge v-if="!site.isActive" tone="neutral">停用</AppBadge>
          <span class="scard__chip scard__chip--status" :class="`scard__chip--${statusTone}`">
            <span class="scard__dot" aria-hidden="true" />
            {{ statusLabel }}
          </span>
        </div>
        <button
          type="button"
          class="scard__url"
          :title="site.url"
          :disabled="sortable"
          @click.stop="openUrl"
        >
          {{ site.url }}
        </button>
      </div>
      <div v-if="!sortable && !menuOpen" class="scard__actions" @click.stop>
        <button
          type="button"
          class="scard__op"
          :class="{ 'is-busy': testing }"
          :disabled="testing"
          :title="testing ? '测试中…' : '测试连通'"
          @click="void testConnectivity()"
        >
          <span class="scard__pulse" :class="`scard__pulse--${statusTone}`" aria-hidden="true" />
        </button>
        <button
          type="button"
          class="scard__op"
          :class="{ 'is-busy': probing }"
          :disabled="probing"
          :title="probing ? '探测中…' : '探测搜索'"
          @click="void probeSearch()"
        >
          <AppIcon name="search" :size="15" />
        </button>
      </div>
    </header>

    <div class="scard__chips">
      <span class="scard__chip tabular" title="优先级">优先级 {{ site.pri }}</span>
      <span v-if="stats && (stats.success || stats.fail)" class="scard__chip tabular" title="成功 / 失败次数">
        {{ stats.success }}/{{ stats.fail }}
      </span>
      <span v-if="site.limitInterval" class="scard__chip">限流</span>
      <span v-if="site.proxy" class="scard__chip">代理</span>
      <span v-if="site.render" class="scard__chip">渲染</span>
      <span v-if="site.filter" class="scard__chip">过滤</span>
    </div>

    <footer class="scard__foot" @click.stop>
      <template v-if="sortable">
        <span class="scard__foot-hint">拖动排序</span>
        <div class="scard__sort">
          <button type="button" class="scard__op" title="上移" @click="emit('move-up')">
            <AppIcon name="chevron-left" :size="14" class="scard__rot-up" />
          </button>
          <button type="button" class="scard__op" title="下移" @click="emit('move-down')">
            <AppIcon name="chevron-right" :size="14" class="scard__rot-down" />
          </button>
        </div>
      </template>
      <template v-else>
        <span class="scard__foot-hint">{{ site.isActive ? '参与聚合搜索' : '已停用，不参与搜索' }}</span>
        <div class="scard__foot-tools">
          <label class="switch scard__switch" :title="site.isActive ? '停用' : '启用'">
            <input
              type="checkbox"
              :checked="site.isActive"
              :aria-label="`启用 ${site.name}`"
              @change="emit('toggle-active', !site.isActive)"
            />
            <span class="switch__track" aria-hidden="true" />
          </label>
          <div class="scard__menu-wrap">
            <button
              type="button"
              class="scard__op"
              title="更多"
              aria-haspopup="menu"
              :aria-expanded="menuOpen"
              @click="menuOpen = !menuOpen"
            >
              <AppIcon name="sliders" :size="15" />
            </button>
            <div v-if="menuOpen" class="scard__menu" role="menu">
              <button type="button" role="menuitem" @click="menuOpen = false; emit('edit')">
                <AppIcon name="edit" :size="14" />
                编辑
              </button>
              <span class="scard__menu-divider" role="separator" />
              <button
                type="button"
                role="menuitem"
                class="scard__menu-danger"
                @click="menuOpen = false; emit('remove')"
              >
                <AppIcon name="trash" :size="14" />
                删除
              </button>
            </div>
          </div>
        </div>
      </template>
    </footer>
  </article>

  <!-- 探测结果单独成窗：列表页里的卡片高度不再被样例撑开 -->
  <AppDialog
    :open="probeOpen"
    :title="`${site.name} · 搜索探测`"
    size="2xl"
    @update:open="(value) => (probeOpen = value)"
  >
    <template #default>
      <div class="probe__meta">
        <span class="probe__url" :title="probeResult?.url || site.url">{{
          probeResult?.url || site.url
        }}</span>
        <span v-if="probeResult" class="probe__elapsed tabular">
          <AppIcon name="timer" :size="13" />
          {{ probeResult.seconds }}s
        </span>
      </div>

      <div v-if="probing" class="probe__loading">
        <span class="probe__spinner" aria-hidden="true" />
        <span>正在抓取搜索页…</span>
      </div>

      <template v-else-if="probeResult">
        <div class="probe__summary" :class="probeResult.ok ? 'is-ok' : 'is-bad'">
          <span class="probe__summary-icon" aria-hidden="true">
            <AppIcon :name="probeResult.ok ? 'check-circle' : 'x-circle'" :size="16" />
          </span>
          <div class="probe__summary-main">
            <span class="probe__status">
              {{ probeResult.ok ? '解析成功' : '探测失败' }}
            </span>
            <span class="probe__status-hint">
              {{
                probeResult.ok
                  ? `搜索页命中 ${probeResult.matched} 个种子，下面只展示前 ${probeResult.samples.length} 条`
                  : probeResult.message
              }}
            </span>
          </div>
        </div>

        <ul v-if="probeResult.ok && probeResult.samples.length" class="probe__list">
          <li v-for="(sample, index) in probeResult.samples" :key="index" class="probe__row">
            <span class="probe__index tabular">{{ index + 1 }}</span>
            <div class="probe__main">
              <div class="probe__title" :title="sample.title">{{ sample.title }}</div>
              <div v-if="sample.subtitle" class="probe__subtitle" :title="sample.subtitle">
                {{ sample.subtitle }}
              </div>
              <div v-if="sampleTags(sample).length" class="probe__tags">
                <span
                  v-for="tag in sampleTags(sample)"
                  :key="tag.label"
                  class="probe__tag"
                  :class="`is-${tag.tone}`"
                  >{{ tag.label }}</span
                >
                <span v-if="sample.promoUntil" class="probe__until tabular">
                  至 {{ formatUntil(sample.promoUntil) }}
                </span>
                <span v-if="sample.bonus" class="probe__bonus tabular">
                  魔力 +{{ sample.bonus.toLocaleString() }}
                </span>
              </div>
            </div>

            <div class="probe__stat">
              <AppIcon name="tag" :size="14" class="probe__stat-icon" />
              <div class="probe__stat-body">
                <span class="probe__stat-value tabular">{{ formatCategory(sample.category) }}</span>
                <span class="probe__stat-label">分类</span>
              </div>
            </div>

            <div class="probe__stat">
              <AppIcon name="hard-drive" :size="14" class="probe__stat-icon" />
              <div class="probe__stat-body">
                <span class="probe__stat-value tabular">{{ formatSize(sample.sizeBytes) }}</span>
                <span class="probe__stat-label">大小</span>
              </div>
            </div>

            <div class="probe__stat">
              <AppIcon name="upload" :size="14" class="probe__stat-icon" />
              <div class="probe__stat-body">
                <span class="probe__stat-value tabular is-up">{{ sample.seeders ?? '—' }}</span>
                <span class="probe__stat-label">做种</span>
              </div>
            </div>

            <div class="probe__stat">
              <AppIcon name="download" :size="14" class="probe__stat-icon" />
              <div class="probe__stat-body">
                <span class="probe__stat-value tabular is-down">{{ sample.resolution || '—' }}</span>
                <span class="probe__stat-label">分辨率</span>
              </div>
            </div>

            <div class="probe__stat">
              <AppIcon name="check-circle" :size="14" class="probe__stat-icon" />
              <div class="probe__stat-body">
                <span class="probe__stat-value tabular">{{ sample.snatched ?? '—' }}</span>
                <span class="probe__stat-label">完成</span>
              </div>
            </div>
          </li>
        </ul>
        <p v-if="probeResult.ok && !probeResult.samples.length" class="probe__msg">
          页面能打开，但没有解析出种子。
        </p>
      </template>
    </template>

    <template #footer>
      <button type="button" class="probe__btn" @click="probeOpen = false">关闭</button>
      <button type="button" class="probe__btn probe__btn--primary" @click="void probeSearch()">
        重试
      </button>
    </template>
  </AppDialog>
</template>

<style scoped>
.scard {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  min-height: 132px;
  padding: var(--space4);
  border-radius: var(--radius-lg);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
  overflow: hidden;
}

.scard:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--color-primary) 28%, var(--panel-border));
  box-shadow: var(--shadow-overlay, var(--shadow-card));
}

.scard--sortable {
  cursor: grab;
}

.scard--sortable:hover {
  transform: none;
}

.scard--inactive {
  opacity: 0.72;
}

/* 顶部细条用整条状态的语义色，替代原先两端透明的渐变 */
.scard__bar {
  position: absolute;
  inset: 0 0 auto;
  height: 2px;
  background: color-mix(in srgb, var(--color-text-tertiary) 40%, transparent);
}

.scard--success .scard__bar {
  background: color-mix(in srgb, var(--color-success) 80%, transparent);
}

.scard--warning .scard__bar {
  background: color-mix(in srgb, var(--color-warning, #d97706) 80%, transparent);
}

.scard--danger .scard__bar {
  background: color-mix(in srgb, var(--color-danger) 80%, transparent);
}

.scard__head {
  display: flex;
  align-items: flex-start;
  gap: var(--space2);
  min-width: 0;
}

.scard__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  margin-top: 1px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  flex-shrink: 0;
  transition:
    background-color 0.18s ease,
    color 0.18s ease;
}

.scard:hover .scard__icon {
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  color: var(--color-primary);
}

.scard__title-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

/* 状态紧贴站点名，属同一层级；其余属性下沉为胶囊 */
.scard__title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.scard__title {
  margin: 0;
  font-size: var(--font-label-size);
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.3;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 属性统一收成一行小标签，省掉标题下方的堆叠 */
.scard__chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 5px;
}

.scard__chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  font-size: 11px;
  line-height: 1.5;
  color: var(--color-text-tertiary);
  background: var(--color-surface-secondary);
}

/* 标题行的状态胶囊：外扩 1px 与 13px 标题视觉等重 */
.scard__chip--status {
  flex: none;
  padding: 1px 6px;
  background: transparent;
  box-shadow: inset 0 0 0 1px color-mix(in srgb, currentColor 24%, transparent);
}

.scard__chip--success {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 10%, transparent);
}

.scard__chip--warning {
  color: var(--color-warning, #d97706);
  background: color-mix(in srgb, var(--color-warning, #d97706) 12%, transparent);
}

.scard__chip--danger {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
}

.scard__chip--status.scard__chip--success,
.scard__chip--status.scard__chip--warning,
.scard__chip--status.scard__chip--danger {
  background: transparent;
}

.scard__url {
  margin: 0;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}

.scard__url:hover:not(:disabled) {
  color: var(--color-primary);
}

.scard__url:disabled {
  cursor: default;
}

.scard__foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space2);
  padding-top: var(--space2);
  border-top: 1px solid var(--panel-divider);
}

.scard__foot-hint {
  font-size: 11px;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.scard__foot-tools {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.scard__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.scard__actions,
.scard__sort {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.scard__op {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.scard__op:hover:not(:disabled) {
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.scard__op:disabled,
.scard__op.is-busy {
  opacity: 0.55;
  cursor: wait;
}

.scard__pulse {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 2px color-mix(in srgb, currentColor 35%, transparent);
  background: currentColor;
  color: var(--color-text-tertiary);
}

.scard__pulse--success {
  color: var(--color-success);
}

.scard__pulse--warning {
  color: var(--color-warning, #d97706);
}

.scard__pulse--danger {
  color: var(--color-danger);
}

.scard__switch {
  transform: scale(0.9);
}

.scard__menu-wrap {
  position: relative;
}

/* 更多菜单：和卡片同一套表面与圆角，靠内边距和分隔线分组 */
.scard__menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 6px);
  z-index: 5;
  min-width: 128px;
  padding: 4px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-overlay, var(--shadow-card));
  transform-origin: bottom right;
  animation: scard-menu-in 0.14s ease-out;
}

@keyframes scard-menu-in {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .scard__menu {
    animation: none;
  }
}

.scard__menu button {
  display: flex;
  align-items: center;
  gap: var(--space2);
  width: 100%;
  padding: 7px 9px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  text-align: left;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background-color 0.12s ease;
}

.scard__menu button .icon {
  color: var(--color-text-tertiary);
  flex: none;
}

.scard__menu button:hover {
  background: var(--color-surface-secondary);
}

.scard__menu-divider {
  display: block;
  height: 1px;
  margin: 3px 2px;
  background: var(--panel-divider);
}

.scard__menu-danger {
  color: var(--color-danger) !important;
}

.scard__menu-danger .icon {
  color: inherit;
}

.scard__menu-danger:hover {
  background: color-mix(in srgb, var(--color-danger) 10%, transparent) !important;
}

.scard__rot-up {
  transform: rotate(90deg);
}

/* 探测弹窗内容：状态行 + 样例列表，弹窗本体负责边框与留白 */
.probe__loading {
  display: flex;
  align-items: center;
  gap: var(--space2);
  padding: var(--space4) 0;
  justify-content: center;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.probe__spinner {
  width: 14px;
  height: 14px;
  border: 2px solid color-mix(in srgb, var(--color-primary) 24%, transparent);
  border-top-color: var(--color-primary);
  border-radius: var(--radius-full);
  animation: probe-spin 0.7s linear infinite;
}

@keyframes probe-spin {
  to {
    transform: rotate(360deg);
  }
}

.probe__summary {
  display: flex;
  align-items: center;
  gap: var(--space3);
  margin-top: var(--space3);
  padding: var(--space3);
  border-radius: var(--radius-md);
}

.probe__summary.is-ok {
  background: color-mix(in srgb, var(--color-success) 8%, transparent);
}

.probe__summary.is-bad {
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
}

.probe__summary-icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
}

.probe__summary.is-ok .probe__summary-icon {
  color: var(--color-success);
}

.probe__summary.is-bad .probe__summary-icon {
  color: var(--color-danger);
}

.probe__summary-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.probe__status {
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.probe__status-hint {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.probe__meta {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-width: 0;
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.probe__url {
  flex: 1;
  min-width: 0;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-secondary);
  font-family: var(--font-mono, ui-monospace, monospace);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.probe__elapsed {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 4px;
}

.probe__msg {
  margin: var(--space3) 0 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.probe__list {
  display: flex;
  flex-direction: column;
  margin: var(--space4) 0 0;
  padding: 0;
  border-top: 1px solid var(--panel-divider);
  list-style: none;
}

.probe__row {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space3) var(--space3) var(--space3) var(--space2);
  border-bottom: 1px solid var(--panel-divider);
  transition: background-color var(--duration-micro) ease;
}

/* 悬停时左侧亮起一道主色竖条，扫读时能锁定当前行 */
.probe__row::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 2px;
  height: 0;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  transform: translateY(-50%);
  transition:
    height var(--duration-micro) ease,
    opacity var(--duration-micro) ease;
  opacity: 0;
}

.probe__row:hover {
  background: var(--color-surface-secondary);
}

.probe__row:hover::before {
  height: 60%;
  opacity: 1;
}

.probe__index {
  display: grid;
  flex: none;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  font-size: 11px;
  color: var(--color-text-tertiary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.probe__row:hover .probe__index {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.probe__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.probe__title {
  font-size: 13px;
  font-weight: var(--font-label-weight);
  line-height: 1.4;
  color: var(--color-text-primary);
  /* 长标题最多两行，超出用省略号，避免单行截断丢太多信息 */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

/* 站点自带的中文译名，层级低于英文标题 */
.probe__subtitle {
  font-size: 12px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.probe__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.probe__tag {
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  line-height: 18px;
  white-space: nowrap;
}

.probe__tag.is-promo {
  background: color-mix(in srgb, var(--color-success) 14%, transparent);
  color: var(--color-success);
}

.probe__tag.is-warn {
  background: color-mix(in srgb, var(--color-danger) 14%, transparent);
  color: var(--color-danger);
}

.probe__tag.is-info {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

.probe__tag.is-accent {
  background: color-mix(in srgb, var(--color-brand-violet) 14%, transparent);
  color: var(--color-brand-violet);
}

/* 促销到期时间与奖励魔力紧跟在促销标签后，弱化成说明文字 */
.probe__until {
  font-size: 11px;
  line-height: 18px;
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.probe__bonus {
  padding: 1px 8px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--color-warning) 14%, transparent);
  font-size: 11px;
  line-height: 18px;
  color: var(--color-warning);
  white-space: nowrap;
}

.probe__stat {
  display: flex;
  flex: none;
  align-items: center;
  gap: 6px;
  width: 86px;
  padding-left: var(--space2);
  border-left: 1px solid var(--panel-divider);
}

.probe__stat-icon {
  flex: none;
  color: color-mix(in srgb, var(--color-text-tertiary) 70%, transparent);
}

.probe__row:hover .probe__stat-icon {
  color: var(--color-text-tertiary);
}

.probe__stat-body {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.probe__stat-value {
  font-size: 12px;
  font-weight: var(--font-label-weight);
  line-height: 1.3;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.probe__stat-value.is-up {
  color: var(--color-success);
}

.probe__stat-value.is-down {
  color: var(--color-primary);
}

.probe__stat-label {
  font-size: 11px;
  line-height: 1.3;
  color: var(--color-text-tertiary);
}

.probe__btn {
  min-width: 76px;
  height: 36px;
  padding: 0 var(--space3);
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.probe__btn--primary {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-on-primary, #fff);
}

.probe__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.scard__rot-down {
  transform: rotate(90deg);
}

.tabular {
  font-variant-numeric: tabular-nums;
}
</style>
