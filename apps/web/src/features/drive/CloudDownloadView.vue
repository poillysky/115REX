<script setup lang="ts">
// 115 云下载：任务列表（下载中 / 失败 / 完成）+ 添加链接任务。
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useNotifyStore } from '@/application/notify'
import DriveEntryIcon from '@/features/drive/DriveEntryIcon.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import { ApiError, describeError } from '@/core/api/error'
import { storageApi } from '@/data/api'
import type { DriveEntry, OfflineQuota, OfflineStatusCounts, OfflineTask } from '@/domain/contract'
import { formatBytes, formatFileTime } from '@/domain/format'

type TabKey = 'downloading' | 'failed' | 'finished'

const router = useRouter()
const notify = useNotifyStore()

const tab = ref<TabKey>('finished')
const tasks = ref<OfflineTask[]>([])
const page = ref(1)
const pageCount = ref(1)
const count = ref(0)
const loading = ref(true)
const errorText = ref('')
const unbound = ref(false)
const quota = ref<OfflineQuota | null>(null)
const counts = ref<OfflineStatusCounts>({
  downloading: 0,
  failed: 0,
  finished: 0,
  total: 0,
})
let loadSeq = 0

const addOpen = ref(false)
const addUrls = ref('')
const addPathId = ref('0')
const folderOptions = ref<{ id: string; name: string }[]>([{ id: '0', name: '根目录' }])
const addBusy = ref(false)
const addError = ref('')

const deleteOpen = ref(false)
const deleteTarget = ref<OfflineTask | null>(null)
const deleteBusy = ref(false)
const deleteError = ref('')
const deleteSource = ref(false)

const tabs = computed(() => [
  { key: 'downloading' as const, label: '正在下载', count: counts.value.downloading },
  { key: 'failed' as const, label: '下载失败', count: counts.value.failed },
  { key: 'finished' as const, label: '完成记录', count: counts.value.finished },
])

const quotaText = computed(() => {
  if (!quota.value) return ''
  return `本月配额：剩 ${quota.value.surplus} / 总 ${quota.value.count}`
})

const emptyCopy = computed(() => {
  if (tab.value === 'downloading') {
    return { title: '暂无下载中的任务', description: '添加链接后，进行中的任务会出现在这里。' }
  }
  if (tab.value === 'failed') {
    return { title: '暂无失败记录', description: '下载失败的任务会集中显示在这里，便于重试或清理。' }
  }
  return { title: '暂无完成记录', description: '下载完成后，记录会保留在此列表。' }
})

function taskIconEntry(task: OfflineTask): DriveEntry {
  const isDir = task.fileCategory === 0 && !!task.fileId
  const name = task.name || task.infoHash
  const ext = isDir ? '' : name.includes('.') ? name.split('.').pop() || '' : ''
  return {
    id: task.infoHash,
    parentId: task.wpPathId || '0',
    name,
    isDir: isDir || !ext,
    size: task.size,
    modifiedAt: task.addTime,
    extension: ext,
  }
}

function percentOf(task: OfflineTask): number {
  return Math.max(0, Math.min(100, Math.round(task.percentDone)))
}

function progressLabel(task: OfflineTask): string {
  if (task.status === 2) return task.statusText || '下载成功'
  if (task.status === -1) return task.statusText || '下载失败'
  if (task.status === 0) return task.statusText || '等待中'
  return task.statusText || `下载中 ${percentOf(task)}%`
}

function isRunning(task: OfflineTask): boolean {
  return task.status === 0 || task.status === 1
}

async function loadQuota(): Promise<void> {
  try {
    quota.value = await storageApi.offlineQuota()
  } catch {
    /* 列表失败时单独处理；配额失败不挡主流程 */
  }
}

async function loadFolders(): Promise<void> {
  try {
    const listing = await storageApi.listFiles({ cid: '0', limit: 200 })
    const folders = listing.entries
      .filter((item) => item.isDir)
      .map((item) => ({ id: item.id, name: item.name }))
    const cloud = folders.find((item) => /云下载|offline|download/i.test(item.name))
    folderOptions.value = [{ id: '0', name: '根目录' }, ...folders]
    if (cloud) {
      addPathId.value = cloud.id
    }
  } catch {
    folderOptions.value = [{ id: '0', name: '根目录' }]
  }
}

async function load(resetPage = false): Promise<void> {
  const seq = ++loadSeq
  if (resetPage) page.value = 1
  loading.value = true
  errorText.value = ''
  unbound.value = false
  try {
    const listing = await storageApi.offlineTasks({
      page: page.value,
      pageSize: 30,
      status: tab.value,
    })
    if (seq !== loadSeq) return
    tasks.value = listing.tasks
    page.value = listing.page
    pageCount.value = listing.pageCount
    count.value = listing.count
    const next = listing.statusCounts
    counts.value = {
      downloading: next.downloading,
      failed: next.failed,
      finished: Math.max(next.finished, counts.value.finished),
      total: Math.max(next.total, counts.value.total),
    }
  } catch (error) {
    if (seq !== loadSeq) return
    if (error instanceof ApiError && error.code === 'STORAGE_AUTH_REQUIRED') {
      unbound.value = true
      tasks.value = []
      errorText.value = ''
    } else {
      errorText.value = describeError(error)
    }
  } finally {
    if (seq === loadSeq) loading.value = false
  }
}

function switchTab(key: TabKey): void {
  if (tab.value === key) return
  tab.value = key
  void load(true)
}

function openAdd(): void {
  addUrls.value = ''
  addError.value = ''
  addOpen.value = true
  void loadFolders()
}

function onPathChange(event: Event): void {
  addPathId.value = (event.target as HTMLSelectElement).value
}

async function submitAdd(): Promise<void> {
  const lines = addUrls.value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
  if (!lines.length) {
    addError.value = '请输入至少一个下载链接'
    return
  }
  addBusy.value = true
  addError.value = ''
  try {
    const { results } = await storageApi.offlineAdd(lines, addPathId.value)
    const failed = results.filter((item) => !item.ok)
    if (failed.length && failed.length === results.length) {
      addError.value = failed[0]?.message || '添加失败'
      return
    }
    addOpen.value = false
    tab.value = failed.length ? 'failed' : 'downloading'
    await load(true)
    void loadQuota()
    if (failed.length) {
      notify.notify(`${failed.length} 条添加失败`, { tone: 'warning' })
    } else {
      notify.success('已开始下载')
    }
  } catch (error) {
    addError.value = describeError(error)
  } finally {
    addBusy.value = false
  }
}

function askDelete(task: OfflineTask): void {
  deleteTarget.value = task
  deleteError.value = ''
  deleteSource.value = false
  deleteOpen.value = true
}

async function submitDelete(): Promise<void> {
  const target = deleteTarget.value
  if (!target) return
  deleteBusy.value = true
  deleteError.value = ''
  try {
    await storageApi.offlineDelete(target.infoHash, deleteSource.value)
    deleteOpen.value = false
    deleteTarget.value = null
    await load()
    void loadQuota()
    notify.success('已删除任务')
  } catch (error) {
    deleteError.value = describeError(error)
  } finally {
    deleteBusy.value = false
  }
}

async function copyUrl(task: OfflineTask): Promise<void> {
  const text = task.url || task.infoHash
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    notify.success('已复制链接')
  } catch {
    notify.failure('复制失败')
  }
}

function viewTask(task: OfflineTask): void {
  const cid = task.fileId || task.wpPathId
  if (!cid) return
  void router.push({ name: 'drive-files', query: { cid } })
}

function goBind(): void {
  void router.push({ name: 'system-115' })
}

function refreshAll(): void {
  void load()
  void loadQuota()
}

function prevPage(): void {
  if (page.value <= 1) return
  page.value -= 1
  void load()
}

function nextPage(): void {
  if (page.value >= pageCount.value) return
  page.value += 1
  void load()
}

onMounted(() => {
  void loadQuota()
  void load(true)
})
</script>

<template>
  <div class="cloud">
    <header class="cloud__toolbar">
      <div class="cloud__actions">
        <AppButton variant="primary" size="sm" :disabled="unbound" @click="openAdd">
          <svg class="cloud__plus" viewBox="0 0 14 14" aria-hidden="true">
            <path
              d="M7 1.5v11M1.5 7h11"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
            />
          </svg>
          添加下载任务
        </AppButton>
        <button
          type="button"
          class="cloud__icon-btn"
          title="刷新"
          aria-label="刷新"
          :disabled="loading"
          @click="refreshAll"
        >
          <AppIcon name="refresh" :size="16" />
        </button>
      </div>

      <div class="cloud__chrome">
        <p v-if="quotaText" class="cloud__quota tabular">{{ quotaText }}</p>
        <nav class="cloud__tabs" aria-label="任务状态">
          <button
            v-for="item in tabs"
            :key="item.key"
            type="button"
            class="cloud__tab"
            :class="{ 'is-active': tab === item.key }"
            :aria-pressed="tab === item.key"
            @click="switchTab(item.key)"
          >
            <span>{{ item.label }}</span>
            <span class="cloud__tab-count tabular">{{ item.count }}</span>
          </button>
        </nav>
      </div>
    </header>

    <AppEmptyState
      v-if="unbound"
      title="尚未绑定 115 网盘"
      description="绑定后即可添加链接任务、查看下载进度与完成记录。"
      icon="folder"
    >
      <AppButton variant="primary" size="sm" @click="goBind">去绑定</AppButton>
    </AppEmptyState>

    <AppErrorState v-else-if="errorText" :message="errorText" @retry="() => load()" />

    <div v-else-if="loading && !tasks.length" class="cloud__skel">
      <AppSkeleton v-for="n in 8" :key="n" height="44px" />
    </div>

    <AppEmptyState
      v-else-if="!loading && !tasks.length"
      :title="emptyCopy.title"
      :description="emptyCopy.description"
      icon="clock"
    >
      <AppButton variant="primary" size="sm" @click="openAdd">添加下载任务</AppButton>
    </AppEmptyState>

    <div v-else class="cloud__table-wrap" :class="{ 'is-loading': loading }">
      <table class="cloud__table">
        <thead>
          <tr>
            <th class="cloud__col-name">
              文件名
              <span v-if="count" class="cloud__summary">共 {{ count }} 项</span>
            </th>
            <th class="cloud__col-time">添加时间</th>
            <th class="cloud__col-size">大小</th>
            <th class="cloud__col-progress">进度</th>
            <th class="cloud__col-ops">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.infoHash" class="cloud__row">
            <td class="cloud__col-name">
              <div class="cloud__name">
                <DriveEntryIcon :entry="taskIconEntry(task)" :size="28" />
                <span class="cloud__name-text" :title="task.name">{{ task.name }}</span>
              </div>
            </td>
            <td class="cloud__col-time tabular">{{ formatFileTime(task.addTime) }}</td>
            <td class="cloud__col-size tabular">{{ formatBytes(task.size) }}</td>
            <td class="cloud__col-progress">
              <div
                class="cloud__status"
                :class="{
                  'is-ok': task.status === 2,
                  'is-fail': task.status === -1,
                  'is-run': isRunning(task),
                }"
              >
                <template v-if="isRunning(task)">
                  <div class="cloud__meter" aria-hidden="true">
                    <span class="cloud__meter-fill" :style="{ width: `${percentOf(task)}%` }" />
                  </div>
                  <span class="cloud__status-text">{{ progressLabel(task) }}</span>
                </template>
                <template v-else>
                  <!-- 完成/失败各两个字，失败原因看 title 提示 -->
                  <span class="cloud__status-text" :title="progressLabel(task)">
                    {{ task.status === 2 ? '成功' : '失败' }}
                  </span>
                </template>
              </div>
            </td>
            <td class="cloud__col-ops">
              <div class="cloud__ops">
                <button
                  type="button"
                  class="cloud__op"
                  title="查看"
                  aria-label="查看网盘位置"
                  :disabled="!task.fileId && !task.wpPathId"
                  @click="viewTask(task)"
                >
                  <AppIcon name="folder" :size="15" />
                </button>
                <button
                  type="button"
                  class="cloud__op"
                  title="复制链接"
                  aria-label="复制链接"
                  :disabled="!task.url && !task.infoHash"
                  @click="copyUrl(task)"
                >
                  <AppIcon name="copy" :size="15" />
                </button>
                <button
                  type="button"
                  class="cloud__op cloud__op--danger"
                  title="删除"
                  aria-label="删除任务"
                  @click="askDelete(task)"
                >
                  <AppIcon name="close" :size="15" />
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <footer v-if="pageCount > 1" class="cloud__pager">
        <AppButton size="sm" :disabled="page <= 1 || loading" @click="prevPage">上一页</AppButton>
        <span class="cloud__pager-text tabular">{{ page }} / {{ pageCount }}</span>
        <AppButton size="sm" :disabled="page >= pageCount || loading" @click="nextPage">下一页</AppButton>
      </footer>
    </div>

    <AppDialog v-model:open="addOpen" title="添加云下载" size="md">
      <div class="add">
        <label class="field">
          <span class="field__label">下载链接</span>
          <textarea
            v-model="addUrls"
            class="field__textarea"
            rows="8"
            placeholder="支持 HTTP、HTTPS、FTP、磁力链和电驴链接，换行可添加多个"
          />
        </label>
        <label class="field field--row">
          <span class="field__label">保存到</span>
          <select class="field__select" :value="addPathId" @change="onPathChange">
            <option v-for="opt in folderOptions" :key="opt.id" :value="opt.id">{{ opt.name }}</option>
          </select>
        </label>
        <p v-if="addError" class="field__hint field__hint--error">{{ addError }}</p>
      </div>
      <template #footer>
        <div class="add__footer">
          <AppButton size="sm" disabled title="暂不支持种子文件，请粘贴磁力链接">添加 BT 任务</AppButton>
          <span class="add__quota">{{ quotaText || '本月配额：—' }}</span>
          <div class="add__footer-right">
            <AppButton size="sm" @click="addOpen = false">取消</AppButton>
            <AppButton size="sm" variant="primary" :loading="addBusy" @click="submitAdd">
              开始下载
            </AppButton>
          </div>
        </div>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="deleteOpen"
      title="删除下载任务？"
      :description="deleteTarget ? `将删除「${deleteTarget.name}」` : ''"
      tone="danger"
      size="sm"
    >
      <label class="field field--check">
        <input v-model="deleteSource" type="checkbox" />
        <span>同时删除已下载到网盘的文件</span>
      </label>
      <p v-if="deleteError" class="field__hint field__hint--error">{{ deleteError }}</p>
      <template #footer>
        <AppButton size="sm" @click="deleteOpen = false">取消</AppButton>
        <AppButton size="sm" variant="danger" :loading="deleteBusy" @click="submitDelete">
          确认删除
        </AppButton>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.cloud {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  min-height: calc(100vh - 120px);
}

.cloud__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  flex-wrap: wrap;
}

.cloud__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space2);
}

.cloud__plus {
  width: 14px;
  height: 14px;
  display: block;
  flex: none;
}

.cloud__icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.cloud__icon-btn:hover:not(:disabled) {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.cloud__icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.cloud__chrome {
  display: inline-flex;
  align-items: center;
  gap: var(--space3);
  flex-wrap: wrap;
  margin-left: auto;
}

.cloud__quota {
  margin: 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
  white-space: nowrap;
}

.cloud__tabs {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.cloud__tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 12px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--font-caption-size);
  white-space: nowrap;
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.cloud__tab:hover {
  color: var(--color-text-primary);
}

.cloud__tab.is-active {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  font-weight: var(--font-label-weight);
}

.cloud__tab-count {
  min-width: 1.25em;
  font-variant-numeric: tabular-nums;
  opacity: 0.78;
}

.cloud__table-wrap {
  position: relative;
  flex: 1;
  overflow: auto;
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.cloud__table-wrap.is-loading {
  opacity: 0.62;
  pointer-events: none;
  transition: opacity var(--duration-micro) ease;
}

.cloud__table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-caption-size);
}

.cloud__table th,
.cloud__table td {
  padding: 11px 16px;
  border-bottom: 1px solid var(--panel-divider);
  text-align: left;
  vertical-align: middle;
}

.cloud__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.cloud__table th:first-child,
.cloud__table td:first-child {
  padding-left: 18px;
}

.cloud__table tbody tr:last-child td {
  border-bottom: 0;
}

.cloud__summary {
  margin-left: var(--space2);
  font-weight: 400;
  color: var(--color-text-tertiary);
}

.cloud__row {
  transition: background-color var(--duration-micro) ease;
}

.cloud__row:hover {
  background: color-mix(in srgb, var(--color-surface-secondary) 85%, transparent);
}

.cloud__col-name {
  min-width: 240px;
}

.cloud__table th.cloud__col-time,
.cloud__table td.cloud__col-time,
.cloud__table th.cloud__col-size,
.cloud__table td.cloud__col-size,
.cloud__table th.cloud__col-progress,
.cloud__table td.cloud__col-progress,
.cloud__table th.cloud__col-ops,
.cloud__table td.cloud__col-ops {
  text-align: center;
}

.cloud__col-time,
.cloud__col-size {
  width: 128px;
  white-space: nowrap;
  color: var(--color-text-secondary);
}

.cloud__col-progress {
  width: 84px;
}

.cloud__col-ops {
  width: 118px;
}

.cloud__name {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  max-width: min(52vw, 640px);
}

.cloud__name-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  color: var(--color-text-primary);
}

.cloud__status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
  max-width: 68px;
  margin-inline: auto;
  padding: 4px 6px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.cloud__status.is-ok {
  align-items: center;
  justify-content: center;
  border-color: color-mix(in srgb, var(--color-success) 24%, var(--panel-border));
  background: color-mix(in srgb, var(--color-success) 8%, var(--color-surface));
  color: var(--color-success);
}

.cloud__status.is-fail {
  align-items: center;
  justify-content: center;
  border-color: color-mix(in srgb, var(--color-danger) 24%, var(--panel-border));
  background: color-mix(in srgb, var(--color-danger) 8%, var(--color-surface));
  color: var(--color-danger);
}

.cloud__status.is-run {
  border-color: color-mix(in srgb, var(--color-warning) 24%, var(--panel-border));
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-surface));
  color: var(--color-warning);
}

.cloud__status-text {
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  line-height: 1.3;
}

.cloud__meter {
  width: 100%;
  max-width: 56px;
  height: 4px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--color-warning) 16%, var(--color-surface-secondary));
  overflow: hidden;
}

.cloud__meter-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-warning);
  transition: width var(--duration-page) ease;
}

.cloud__ops {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}

.cloud__op {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.cloud__op:hover:not(:disabled) {
  color: var(--color-primary);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
}

.cloud__op--danger:hover:not(:disabled) {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
}

.cloud__op:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.cloud__skel {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  padding: var(--space6);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.cloud__pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space3);
  padding: 12px 16px;
  border-top: 1px solid var(--panel-divider);
}

.cloud__pager-text {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.add {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.add__footer {
  display: flex;
  align-items: center;
  gap: var(--space3);
  width: 100%;
  flex-wrap: wrap;
}

.add__quota {
  flex: 1;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
  min-width: 140px;
}

.add__footer-right {
  display: inline-flex;
  gap: var(--space2);
  margin-left: auto;
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space1);
  min-width: 0;
}

.field--row {
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.field--check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.field--check input {
  width: 15px;
  height: 15px;
  accent-color: var(--color-primary);
}

.field__label {
  white-space: nowrap;
}

.field--row .field__select {
  flex: 1;
  min-width: 0;
}

.field__textarea {
  min-height: 160px;
}

.tabular {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}

@media (max-width: 860px) {
  .cloud__chrome {
    width: 100%;
    margin-left: 0;
    justify-content: space-between;
  }

  .cloud__tabs {
    width: 100%;
    overflow-x: auto;
  }

  .cloud__quota {
    display: none;
  }

  .cloud__col-time,
  .cloud__col-size {
    display: none;
  }

  .cloud__name {
    max-width: 58vw;
  }
}
</style>
