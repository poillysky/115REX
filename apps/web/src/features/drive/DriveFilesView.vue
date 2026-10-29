<script setup lang="ts">
// 115 文件浏览：列表 + 面包屑 + 基础操作（进入目录 / 新建 / 重命名 / 删除）。
// 上传与筛选按钮先占位，接入后替换。
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import DriveEntryIcon from '@/features/drive/DriveEntryIcon.vue'
import {
  TEXT_PREVIEW_MAX_BYTES,
  canPreview,
  previewKindOf,
  type PreviewKind,
} from '@/features/drive/previewKinds'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import { describeError } from '@/core/api/error'
import { ApiError } from '@/core/api/error'
import { sessionStore } from '@/core/session'
import { storageApi } from '@/data/api'
import type { DriveEntry, DrivePathNode } from '@/domain/contract'
import { formatBytes, formatFileTime } from '@/domain/format'

type SortKey = 'name' | 'size' | 'type' | 'modified'
type ViewMode = 'list' | 'grid'

const route = useRoute()
const router = useRouter()

const cid = ref('0')
const path = ref<DrivePathNode[]>([{ cid: '0', name: '根目录' }])
const entries = ref<DriveEntry[]>([])
const count = ref(0)
const loading = ref(true)
const navigating = ref(false)
const errorText = ref('')
const unbound = ref(false)
let loadSeq = 0

const selected = ref<Set<string>>(new Set())
const sortKey = ref<SortKey>('modified')
const sortAsc = ref(false)
const viewMode = ref<ViewMode>('list')

const mkdirOpen = ref(false)
const mkdirName = ref('')
const mkdirBusy = ref(false)
const mkdirError = ref('')

const renameOpen = ref(false)
const renameTarget = ref<DriveEntry | null>(null)
const renameName = ref('')
const renameBusy = ref(false)
const renameError = ref('')

const deleteOpen = ref(false)
const deleteBusy = ref(false)
const deleteError = ref('')
const moreOpen = ref(false)

const previewOpen = ref(false)
const previewBusy = ref(false)
const previewError = ref('')
const previewKind = ref<PreviewKind>('image')
const previewUrl = ref('')
const previewName = ref('')
const previewText = ref('')
const previewVideoEl = ref<HTMLVideoElement | null>(null)

const folderCount = computed(() => entries.value.filter((item) => item.isDir).length)
const fileCount = computed(() => entries.value.length - folderCount.value)
const selectedCount = computed(() => selected.value.size)
const allSelected = computed(
  () => entries.value.length > 0 && selected.value.size === entries.value.length,
)

const sortedEntries = computed(() => {
  const list = [...entries.value]
  const dirFirst = (a: DriveEntry, b: DriveEntry) => Number(b.isDir) - Number(a.isDir)
  const factor = sortAsc.value ? 1 : -1
  list.sort((a, b) => {
    const byDir = dirFirst(a, b)
    if (byDir !== 0) return byDir
    if (sortKey.value === 'name') return a.name.localeCompare(b.name, 'zh') * factor
    if (sortKey.value === 'size') return (a.size - b.size) * factor
    if (sortKey.value === 'type') {
      const ta = a.isDir ? '文件夹' : a.extension || '文件'
      const tb = b.isDir ? '文件夹' : b.extension || '文件'
      return ta.localeCompare(tb, 'zh') * factor
    }
    return (a.modifiedAt - b.modifiedAt) * factor
  })
  return list
})

const summaryText = computed(() => {
  if (!entries.value.length) return '当前目录为空'
  const parts: string[] = []
  if (folderCount.value) parts.push(`${folderCount.value}个文件夹`)
  if (fileCount.value) parts.push(`${fileCount.value}个文件`)
  return `当前共${parts.join('、')}`
})

function sortMark(key: SortKey): string {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? '↑' : '↓'
}

function closeMore(): void {
  moreOpen.value = false
}

function typeLabel(entry: DriveEntry): string {
  if (entry.isDir) return '文件夹'
  return entry.extension ? entry.extension.toUpperCase() : '文件'
}

function sizeLabel(entry: DriveEntry): string {
  return entry.isDir ? '' : formatBytes(entry.size)
}

function toggleSort(key: SortKey): void {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
    return
  }
  sortKey.value = key
  sortAsc.value = key === 'name'
}

function isSelected(id: string): boolean {
  return selected.value.has(id)
}

function toggleOne(id: string): void {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function toggleAll(): void {
  if (allSelected.value) {
    selected.value = new Set()
    return
  }
  selected.value = new Set(entries.value.map((item) => item.id))
}

async function load(targetCid = cid.value, soft = false): Promise<void> {
  const seq = ++loadSeq
  const softNav = soft && entries.value.length > 0 && !unbound.value
  if (softNav) navigating.value = true
  else loading.value = true
  errorText.value = ''
  unbound.value = false
  selected.value = new Set()
  // 立刻更新路径感，避免点了没反应
  if (softNav) cid.value = targetCid
  try {
    const listing = await storageApi.listFiles({
      cid: targetCid,
      order: 'user_utime',
      asc: false,
      limit: 200,
    })
    if (seq !== loadSeq) return
    cid.value = listing.cid || targetCid
    path.value = listing.path.length ? listing.path : [{ cid: '0', name: '根目录' }]
    entries.value = listing.entries
    count.value = listing.count
  } catch (error) {
    if (seq !== loadSeq) return
    if (error instanceof ApiError && error.code === 'STORAGE_AUTH_REQUIRED') {
      unbound.value = true
      entries.value = []
      count.value = 0
      errorText.value = ''
    } else {
      errorText.value = describeError(error)
    }
  } finally {
    if (seq === loadSeq) {
      loading.value = false
      navigating.value = false
    }
  }
}

function canOpen(entry: DriveEntry): boolean {
  if (entry.isDir) return true
  return canPreview(entry.extension, entry.name)
}

function openEntry(entry: DriveEntry): void {
  if (entry.isDir) {
    void load(entry.id, true)
    return
  }
  const kind = previewKindOf(entry.extension, entry.name)
  if (!kind) return
  void openPreview(entry, kind)
}

function onRowClick(entry: DriveEntry): void {
  // 文件夹单击即进；文件单击勾选（双击 / 点文件名再打开）
  if (entry.isDir) {
    openEntry(entry)
    return
  }
  toggleOne(entry.id)
}

function streamUrl(pickCode: string): string {
  const token = sessionStore.access() || ''
  const params = new URLSearchParams({
    pickCode,
    accessToken: token,
  })
  return `/api/v1/storage/115/files/stream?${params.toString()}`
}

async function loadTextPreview(url: string, size: number): Promise<void> {
  if (size > TEXT_PREVIEW_MAX_BYTES) {
    previewError.value = `文本过大（${formatBytes(size)}），请新窗口打开或下载查看`
    return
  }
  const response = await fetch(url)
  if (!response.ok) throw new Error(`加载失败（${response.status}）`)
  const lengthHeader = Number(response.headers.get('content-length') || 0)
  if (lengthHeader > TEXT_PREVIEW_MAX_BYTES) {
    previewError.value = `文本过大（${formatBytes(lengthHeader)}），请新窗口打开或下载查看`
    return
  }
  const buffer = await response.arrayBuffer()
  if (buffer.byteLength > TEXT_PREVIEW_MAX_BYTES) {
    previewError.value = `文本过大（${formatBytes(buffer.byteLength)}），请新窗口打开或下载查看`
    return
  }
  previewText.value = new TextDecoder('utf-8', { fatal: false }).decode(buffer)
}

async function resolveEntry(entry: DriveEntry): Promise<DriveEntry> {
  if (entry.pickCode) return entry
  // 旧列表缓存可能缺 pickCode：重拉当前目录再按 id 对齐
  try {
    const listing = await storageApi.listFiles({
      cid: entry.parentId || cid.value,
      order: 'user_utime',
      asc: false,
      limit: 500,
    })
    const fresh = listing.entries.find((item) => item.id === entry.id)
    if (fresh?.pickCode) {
      entries.value = listing.entries
      path.value = listing.path.length ? listing.path : path.value
      return fresh
    }
  } catch {
    /* 下面统一报缺标识 */
  }
  return entry
}

async function openPreview(entry: DriveEntry, kind: PreviewKind): Promise<void> {
  previewName.value = entry.name
  previewKind.value = kind
  previewError.value = ''
  previewText.value = ''
  previewBusy.value = true
  previewOpen.value = true
  previewUrl.value = ''

  const target = await resolveEntry(entry)

  // 图片：列表大图即可；其余一律走本机代理（CDN 校验 UA）
  if (kind === 'image' && (target.previewUrl || entry.previewUrl)) {
    previewUrl.value = target.previewUrl || entry.previewUrl || ''
    previewBusy.value = false
    return
  }

  if (!target.pickCode) {
    previewBusy.value = false
    previewError.value = '无法打开：缺少文件标识，请刷新目录后重试'
    return
  }

  const url = streamUrl(target.pickCode)
  previewUrl.value = url

  if (kind === 'text') {
    try {
      await loadTextPreview(url, target.size || entry.size || 0)
    } catch (error) {
      previewError.value = describeError(error)
    } finally {
      previewBusy.value = false
    }
    return
  }

  previewBusy.value = false
}

function closePreview(): void {
  if (document.fullscreenElement) void document.exitFullscreen()
  previewOpen.value = false
  previewUrl.value = ''
  previewText.value = ''
  previewError.value = ''
  previewVideoEl.value = null
}

function openInNewTab(url: string): void {
  window.open(url, '_blank', 'noopener,noreferrer')
}

async function togglePreviewFullscreen(): Promise<void> {
  const el = previewVideoEl.value
  if (!el) return
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
      return
    }
    if (el.requestFullscreen) await el.requestFullscreen()
    else if ('webkitEnterFullscreen' in el) {
      ;(el as HTMLVideoElement & { webkitEnterFullscreen: () => void }).webkitEnterFullscreen()
    }
  } catch {
    previewError.value = '无法进入全屏'
  }
}

function goPath(node: DrivePathNode): void {
  void load(node.cid, true)
}

function openMkdir(): void {
  mkdirName.value = ''
  mkdirError.value = ''
  mkdirOpen.value = true
}

async function submitMkdir(): Promise<void> {
  const name = mkdirName.value.trim()
  if (!name) {
    mkdirError.value = '请填写文件夹名称'
    return
  }
  mkdirBusy.value = true
  mkdirError.value = ''
  try {
    await storageApi.mkdir(cid.value, name)
    mkdirOpen.value = false
    await load(cid.value)
  } catch (error) {
    mkdirError.value = describeError(error)
  } finally {
    mkdirBusy.value = false
  }
}

function openRename(): void {
  const id = [...selected.value][0]
  const target = entries.value.find((item) => item.id === id)
  if (!target) return
  renameTarget.value = target
  renameName.value = target.name
  renameError.value = ''
  renameOpen.value = true
}

async function submitRename(): Promise<void> {
  const target = renameTarget.value
  const name = renameName.value.trim()
  if (!target || !name) {
    renameError.value = '请填写新名称'
    return
  }
  renameBusy.value = true
  renameError.value = ''
  try {
    await storageApi.rename(target.id, name)
    renameOpen.value = false
    await load(cid.value)
  } catch (error) {
    renameError.value = describeError(error)
  } finally {
    renameBusy.value = false
  }
}

function openDelete(): void {
  if (!selected.value.size) return
  deleteError.value = ''
  deleteOpen.value = true
}

async function submitDelete(): Promise<void> {
  deleteBusy.value = true
  deleteError.value = ''
  try {
    await storageApi.deleteFiles([...selected.value])
    deleteOpen.value = false
    await load(cid.value)
  } catch (error) {
    deleteError.value = describeError(error)
  } finally {
    deleteBusy.value = false
  }
}

function goBind(): void {
  void router.push({ name: 'system-115' })
}

onMounted(() => {
  const q = String(route.query.cid || '').trim()
  void load(q || '0')
})
</script>

<template>
  <div class="drive" @click="closeMore">
    <header class="drive__toolbar">
      <div class="drive__actions">
        <AppButton
          size="sm"
          variant="primary"
          class="drive__stub"
          title="上传尚未接入"
          aria-disabled="true"
          @click.prevent
        >
          <AppIcon name="cloud-down" :size="15" />
          上传
        </AppButton>
        <AppButton size="sm" :disabled="unbound || loading" @click="openMkdir">
          <svg class="drive__plus" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
            <path
              d="M8 2.75a.75.75 0 0 1 .75.75v3.75h3.75a.75.75 0 0 1 0 1.5H8.75v3.75a.75.75 0 0 1-1.5 0V8.75H3.5a.75.75 0 0 1 0-1.5h3.75V3.5A.75.75 0 0 1 8 2.75Z"
              fill="currentColor"
            />
          </svg>
          新建
        </AppButton>
        <AppButton
          size="sm"
          class="drive__stub"
          title="筛选尚未接入"
          aria-disabled="true"
          @click.prevent
        >
          <AppIcon name="sliders" :size="14" />
          筛选
        </AppButton>
        <template v-if="selectedCount">
          <span class="drive__sep" aria-hidden="true" />
          <AppButton size="sm" :disabled="selectedCount !== 1" @click="openRename">重命名</AppButton>
          <AppButton size="sm" @click="openDelete">删除</AppButton>
        </template>
      </div>

      <div class="drive__chrome">
        <div class="drive__view" role="group" aria-label="视图切换">
          <button
            type="button"
            class="drive__view-btn"
            :class="{ 'is-active': viewMode === 'list' }"
            title="列表视图"
            :aria-pressed="viewMode === 'list'"
            @click="viewMode = 'list'"
          >
            <AppIcon name="list" :size="16" />
          </button>
          <button
            type="button"
            class="drive__view-btn"
            :class="{ 'is-active': viewMode === 'grid' }"
            title="图标视图"
            :aria-pressed="viewMode === 'grid'"
            @click="viewMode = 'grid'"
          >
            <AppIcon name="grid" :size="16" />
          </button>
        </div>

        <div class="drive__more" @click.stop>
          <button
            type="button"
            class="drive__more-btn"
            title="更多"
            :aria-expanded="moreOpen"
            aria-haspopup="menu"
            @click="moreOpen = !moreOpen"
          >
            <span class="drive__dots" aria-hidden="true" />
          </button>
          <div v-if="moreOpen" class="drive__menu" role="menu">
            <button
              type="button"
              class="drive__menu-item"
              role="menuitem"
              :disabled="loading"
              @click="closeMore(); void load(cid)"
            >
              <AppIcon name="refresh" :size="14" />
              刷新
            </button>
            <button
              type="button"
              class="drive__menu-item"
              role="menuitem"
              :disabled="selectedCount !== 1 || unbound"
              @click="closeMore(); openRename()"
            >
              重命名
            </button>
            <button
              type="button"
              class="drive__menu-item is-danger"
              role="menuitem"
              :disabled="!selectedCount || unbound"
              @click="closeMore(); openDelete()"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </header>

    <nav class="drive__crumb" aria-label="当前路径">
      <template v-for="(node, index) in path" :key="node.cid">
        <span v-if="index > 0" class="drive__crumb-sep" aria-hidden="true">/</span>
        <button
          type="button"
          class="drive__crumb-item"
          :class="{ 'is-current': index === path.length - 1 }"
          :disabled="index === path.length - 1"
          @click="goPath(node)"
        >
          {{ node.name }}
        </button>
      </template>
    </nav>

    <AppErrorState v-if="errorText" :message="errorText" @retry="() => load(cid)" />

    <div v-else-if="unbound" class="drive__empty">
      <p class="drive__empty-title">尚未绑定 115 网盘</p>
      <p class="drive__empty-desc">绑定后即可在这里浏览文件、新建文件夹与删除。</p>
      <AppButton size="sm" variant="primary" @click="goBind">去绑定</AppButton>
    </div>

    <div v-else-if="loading" class="drive__skel">
      <AppSkeleton height="44px" width="100%" />
      <AppSkeleton height="44px" width="100%" />
      <AppSkeleton height="44px" width="100%" />
      <AppSkeleton height="44px" width="100%" />
    </div>

    <div
      v-else-if="viewMode === 'list'"
      class="drive__table-wrap"
      :class="{ 'is-navigating': navigating }"
    >
      <table class="drive__table">
        <thead>
          <tr>
            <th class="drive__check">
              <input
                type="checkbox"
                :checked="allSelected"
                :indeterminate.prop="selectedCount > 0 && !allSelected"
                aria-label="全选"
                @change="toggleAll"
              />
            </th>
            <th class="drive__col-name">
              <button type="button" class="drive__sort" @click="toggleSort('name')">
                文件名
                <span v-if="sortMark('name')" class="drive__sort-mark is-on">{{ sortMark('name') }}</span>
              </button>
              <span class="drive__summary">{{ summaryText }}</span>
            </th>
            <th class="drive__col-size">
              <button type="button" class="drive__sort" @click="toggleSort('size')">
                大小
                <span v-if="sortMark('size')" class="drive__sort-mark is-on">{{ sortMark('size') }}</span>
              </button>
            </th>
            <th class="drive__col-type">
              <button type="button" class="drive__sort" @click="toggleSort('type')">
                种类
                <span v-if="sortMark('type')" class="drive__sort-mark is-on">{{ sortMark('type') }}</span>
              </button>
            </th>
            <th class="drive__col-time">
              <button type="button" class="drive__sort" @click="toggleSort('modified')">
                修改时间
                <span v-if="sortMark('modified')" class="drive__sort-mark is-on">{{
                  sortMark('modified')
                }}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!sortedEntries.length">
            <td colspan="5" class="drive__blank">这个文件夹是空的</td>
          </tr>
          <tr
            v-for="entry in sortedEntries"
            :key="entry.id"
            class="drive__row"
            :class="{ 'is-selected': isSelected(entry.id), 'is-dir': entry.isDir }"
            @click="onRowClick(entry)"
            @dblclick="openEntry(entry)"
          >
            <td class="drive__check" @click.stop>
              <input
                type="checkbox"
                :checked="isSelected(entry.id)"
                :aria-label="`选择 ${entry.name}`"
                @change="toggleOne(entry.id)"
              />
            </td>
            <td class="drive__col-name">
              <button
                type="button"
                class="drive__name"
                :class="{ 'is-openable': canOpen(entry) }"
                :disabled="!canOpen(entry)"
                @click.stop="openEntry(entry)"
              >
                <DriveEntryIcon :entry="entry" :size="28" />
                <span class="drive__filename">{{ entry.name }}</span>
              </button>
            </td>
            <td class="drive__col-size tabular">{{ sizeLabel(entry) }}</td>
            <td class="drive__col-type">{{ typeLabel(entry) }}</td>
            <td class="drive__col-time tabular">{{ formatFileTime(entry.modifiedAt) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="drive__grid" :class="{ 'is-navigating': navigating }">
      <button
        v-for="entry in sortedEntries"
        :key="entry.id"
        type="button"
        class="drive__card"
        :class="{ 'is-selected': isSelected(entry.id) }"
        @click="onRowClick(entry)"
        @dblclick="openEntry(entry)"
      >
        <DriveEntryIcon :entry="entry" :size="48" />
        <span class="drive__card-name">{{ entry.name }}</span>
        <span class="drive__card-meta">{{ typeLabel(entry) }}</span>
      </button>
      <p v-if="!sortedEntries.length" class="drive__blank">这个文件夹是空的</p>
    </div>

    <AppDialog v-model:open="mkdirOpen" title="新建文件夹" size="sm">
      <label class="field">
        <span class="field__label">名称</span>
        <input
          v-model="mkdirName"
          class="field__input"
          type="text"
          maxlength="128"
          placeholder="新建文件夹"
          @keydown.enter.prevent="submitMkdir"
        />
      </label>
      <p v-if="mkdirError" class="field__error">{{ mkdirError }}</p>
      <template #footer>
        <AppButton size="sm" @click="mkdirOpen = false">取消</AppButton>
        <AppButton size="sm" variant="primary" :loading="mkdirBusy" @click="submitMkdir">
          创建
        </AppButton>
      </template>
    </AppDialog>

    <AppDialog v-model:open="renameOpen" title="重命名" size="sm">
      <label class="field">
        <span class="field__label">新名称</span>
        <input
          v-model="renameName"
          class="field__input"
          type="text"
          maxlength="128"
          @keydown.enter.prevent="submitRename"
        />
      </label>
      <p v-if="renameError" class="field__error">{{ renameError }}</p>
      <template #footer>
        <AppButton size="sm" @click="renameOpen = false">取消</AppButton>
        <AppButton size="sm" variant="primary" :loading="renameBusy" @click="submitRename">
          保存
        </AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="deleteOpen"
      title="删除所选项目？"
      :description="`将删除 ${selectedCount} 项，可在 115 回收站找回。`"
      tone="danger"
      size="sm"
    >
      <p v-if="deleteError" class="field__error">{{ deleteError }}</p>
      <template #footer>
        <AppButton size="sm" @click="deleteOpen = false">取消</AppButton>
        <AppButton size="sm" variant="danger" :loading="deleteBusy" @click="submitDelete">
          确认删除
        </AppButton>
      </template>
    </AppDialog>

    <Teleport to="body">
      <div
        v-if="previewOpen"
        class="preview"
        :class="{
          'preview--video': previewKind === 'video',
          'preview--audio': previewKind === 'audio',
          'preview--text': previewKind === 'text',
          'preview--pdf': previewKind === 'pdf',
        }"
        role="dialog"
        aria-modal="true"
        :aria-label="previewName || '预览'"
        @click.self="closePreview"
        @keydown.esc.prevent="closePreview"
      >
        <div class="preview__panel">
          <header class="preview__head">
            <span class="preview__badge" aria-hidden="true">
              <AppIcon
                :name="
                  previewKind === 'video'
                    ? 'film'
                    : previewKind === 'audio'
                      ? 'music'
                      : previewKind === 'image'
                        ? 'image'
                        : 'folder'
                "
                :size="16"
              />
            </span>
            <h2 class="preview__title" :title="previewName">{{ previewName }}</h2>
            <div class="preview__tools">
              <button
                v-if="previewKind === 'video' && previewUrl && !previewBusy"
                type="button"
                class="preview__tool"
                title="全屏"
                @click="togglePreviewFullscreen"
              >
                <AppIcon name="fullscreen" :size="16" />
                <span>全屏</span>
              </button>
              <button
                v-if="previewUrl && !previewBusy"
                type="button"
                class="preview__tool"
                title="新窗口打开"
                @click="openInNewTab(previewUrl)"
              >
                <AppIcon name="link" :size="16" />
              </button>
              <button
                type="button"
                class="preview__tool preview__tool--close"
                aria-label="关闭"
                title="关闭"
                @click="closePreview"
              >
                <AppIcon name="close" :size="16" />
              </button>
            </div>
          </header>
          <div class="preview__body">
            <p v-if="previewBusy" class="preview__hint">正在加载…</p>
            <template v-else-if="previewError">
              <p class="preview__hint is-error">{{ previewError }}</p>
              <button
                v-if="previewUrl"
                type="button"
                class="preview__retry"
                @click="openInNewTab(previewUrl)"
              >
                新窗口打开
              </button>
            </template>
            <img
              v-else-if="previewKind === 'image' && previewUrl"
              class="preview__media preview__media--image"
              :src="previewUrl"
              :alt="previewName"
            />
            <video
              v-else-if="previewKind === 'video' && previewUrl"
              ref="previewVideoEl"
              class="preview__media preview__media--video"
              :src="previewUrl"
              controls
              autoplay
              playsinline
              preload="auto"
              @error="previewError = '视频加载失败，请重试或新窗口打开'"
              @dblclick="togglePreviewFullscreen"
            />
            <div v-else-if="previewKind === 'audio' && previewUrl" class="preview__audio">
              <span class="preview__audio-art" aria-hidden="true">
                <AppIcon name="music" :size="40" />
              </span>
              <p class="preview__audio-name">{{ previewName }}</p>
              <audio
                class="preview__media preview__media--audio"
                :src="previewUrl"
                controls
                autoplay
                preload="metadata"
                @error="previewError = '音频加载失败，请重试或新窗口打开'"
              />
            </div>
            <iframe
              v-else-if="previewKind === 'pdf' && previewUrl"
              class="preview__media preview__media--pdf"
              :src="previewUrl"
              title="PDF 预览"
            />
            <pre
              v-else-if="previewKind === 'text' && previewText"
              class="preview__text"
            >{{ previewText }}</pre>
            <p v-else class="preview__hint">暂无可预览内容</p>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.drive {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  min-height: calc(100vh - 120px);
}

.drive__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  flex-wrap: wrap;
}

.drive__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space2);
}

/* 占位动作：保持样图主色/白底，不走 disabled 灰态 */
.drive__stub {
  cursor: not-allowed;
  opacity: 1;
}

.drive__plus {
  flex: none;
  width: 14px;
  height: 14px;
  display: block;
}

.drive__sep {
  width: 1px;
  height: 18px;
  margin: 0 var(--space1);
  background: var(--panel-divider);
}

.drive__chrome {
  display: inline-flex;
  align-items: center;
  gap: var(--space2);
}

.drive__view {
  display: inline-flex;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.drive__view-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.drive__view-btn:hover {
  color: var(--color-text-primary);
}

.drive__view-btn.is-active {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
}

.drive__more {
  position: relative;
}

.drive__more-btn {
  display: grid;
  place-items: center;
  width: 34px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.drive__more-btn:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.drive__dots {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: currentColor;
  box-shadow:
    0 -6px 0 currentColor,
    0 6px 0 currentColor;
}

.drive__menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  z-index: 5;
  min-width: 132px;
  padding: var(--space1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-overlay);
}

.drive__menu-item {
  display: flex;
  align-items: center;
  gap: var(--space2);
  width: 100%;
  min-height: 34px;
  padding: 0 var(--space3);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-size: var(--font-caption-size);
  text-align: left;
}

.drive__menu-item:hover:not(:disabled) {
  background: var(--color-surface-secondary);
}

.drive__menu-item:disabled {
  opacity: 0.4;
}

.drive__menu-item.is-danger {
  color: var(--color-danger);
}

.drive__crumb {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
  min-height: 24px;
  font-size: var(--font-caption-size);
}

.drive__crumb-item {
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  padding: 2px 4px;
}

.drive__crumb-item:hover:not(:disabled) {
  color: var(--color-primary);
}

.drive__crumb-item.is-current {
  color: var(--color-text-primary);
  font-weight: var(--font-label-weight);
}

.drive__crumb-sep {
  color: var(--color-text-tertiary);
}

.drive__table-wrap {
  position: relative;
  flex: 1;
  overflow: auto;
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.drive__table-wrap.is-navigating,
.drive__grid.is-navigating {
  opacity: 0.55;
  pointer-events: none;
  transition: opacity var(--duration-micro) ease;
}

.drive__table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-caption-size);
}

.drive__table th,
.drive__table td {
  padding: 11px 16px;
  border-bottom: 1px solid var(--panel-divider);
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
}

.drive__table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.drive__table th:first-child,
.drive__table td:first-child {
  padding-left: 18px;
}

.drive__table tbody tr:last-child td {
  border-bottom: 0;
}

.drive__check {
  width: 44px;
}

.drive__check input {
  width: 15px;
  height: 15px;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.drive__col-name {
  min-width: 220px;
}

.drive__col-size {
  width: 108px;
  color: var(--color-text-secondary);
}

.drive__col-type {
  width: 100px;
  color: var(--color-text-secondary);
}

.drive__col-time {
  width: 148px;
  color: var(--color-text-secondary);
}

.drive__sort {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: inherit;
}

.drive__sort-mark {
  font-size: 11px;
  color: var(--color-text-primary);
}

.drive__summary {
  margin-left: var(--space2);
  font-weight: 400;
  color: var(--color-text-tertiary);
}

.drive__row {
  cursor: default;
  transition: background-color var(--duration-micro) ease;
}

.drive__row:hover {
  background: color-mix(in srgb, var(--color-surface-secondary) 85%, transparent);
}

.drive__row.is-selected {
  background: color-mix(in srgb, var(--color-primary-subtle) 80%, transparent);
}

.drive__name {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  max-width: min(52vw, 640px);
  color: var(--color-text-primary);
  text-align: left;
}

.drive__name:disabled {
  cursor: default;
}

.drive__name.is-openable:hover .drive__filename {
  color: var(--color-primary);
}

.drive__filename {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  color: var(--color-text-primary);
}

.tabular {
  font-variant-numeric: tabular-nums;
}

.drive__blank {
  padding: var(--space10);
  text-align: center;
  color: var(--color-text-secondary);
}

.drive__empty,
.drive__skel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space3);
  padding: var(--space10) var(--space6);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.drive__empty-title {
  margin: 0;
  font-size: var(--font-label-size);
  font-weight: 600;
}

.drive__empty-desc {
  margin: 0 0 var(--space2);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.drive__skel {
  align-items: stretch;
}

.drive__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: var(--space2);
  padding: var(--space3);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.drive__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space2);
  padding: var(--space4) var(--space2) var(--space3);
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  color: var(--color-text-primary);
  transition: background-color var(--duration-micro) ease;
}

.drive__card:hover {
  background: var(--color-surface-secondary);
}

.drive__card.is-selected {
  border-color: color-mix(in srgb, var(--color-primary) 28%, var(--panel-border));
  background: var(--color-primary-subtle);
}

.drive__card-name {
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  text-align: center;
}

.drive__card-meta {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.field {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
}

.field__label {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.field__error {
  margin: var(--space2) 0 0;
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.preview {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: clamp(12px, 2.5vw, 28px);
  background: color-mix(in srgb, #05070c 72%, transparent);
  backdrop-filter: blur(10px);
  animation: preview-in 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes preview-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.preview__panel {
  display: flex;
  flex-direction: column;
  width: min(1100px, 100%);
  max-height: min(92vh, 960px);
  border: 1px solid color-mix(in srgb, #fff 8%, transparent);
  border-radius: 16px;
  background: var(--color-surface);
  box-shadow:
    0 1px 0 color-mix(in srgb, #fff 6%, transparent) inset,
    0 24px 64px color-mix(in srgb, #000 45%, transparent);
  overflow: hidden;
  animation: preview-panel-in 220ms cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes preview-panel-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.985);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.preview--video .preview__panel,
.preview--pdf .preview__panel {
  width: min(1280px, 100%);
  height: min(92vh, 900px);
  max-height: none;
}

.preview--video .preview__panel {
  background: #0a0c11;
  color: #f4f6fb;
}

.preview--text .preview__panel {
  width: min(980px, 100%);
  height: min(88vh, 860px);
  max-height: none;
}

.preview--audio .preview__panel {
  width: min(480px, 100%);
}

.preview__head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
  min-height: 52px;
  padding: 0 12px 0 14px;
  border-bottom: 1px solid var(--panel-divider);
  background: color-mix(in srgb, var(--color-surface) 92%, var(--color-surface-secondary));
}

.preview--video .preview__head {
  border-bottom-color: rgb(255 255 255 / 0.06);
  background: linear-gradient(180deg, #161a24 0%, #12151d 100%);
}

.preview__badge {
  flex: none;
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--color-primary) 14%, transparent);
  color: var(--color-primary);
}

.preview--video .preview__badge {
  background: color-mix(in srgb, var(--color-primary) 28%, transparent);
  color: #9ec1ff;
}

.preview__title {
  flex: 1;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.preview__tools {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: none;
}

.preview__tool {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 34px;
  height: 34px;
  padding: 0 10px;
  border-radius: 10px;
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.preview__tool span {
  font-size: 12px;
  font-weight: 600;
}

.preview--video .preview__tool {
  color: rgb(244 246 251 / 0.72);
}

.preview__tool:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.preview--video .preview__tool:hover {
  background: rgb(255 255 255 / 0.08);
  color: #fff;
}

.preview__tool--close:hover {
  background: color-mix(in srgb, var(--color-danger) 14%, transparent);
  color: var(--color-danger);
}

.preview--video .preview__tool--close:hover {
  background: color-mix(in srgb, var(--color-danger) 28%, transparent);
  color: #ffb4b8;
}

.preview__body {
  flex: 1;
  display: grid;
  place-items: center;
  min-height: 0;
  padding: 0;
  overflow: hidden;
  background: #000;
}

.preview:not(.preview--video) .preview__body {
  min-height: 320px;
  padding: var(--space4);
  overflow: auto;
  background: color-mix(in srgb, var(--color-surface-secondary) 70%, #000 4%);
}

.preview--pdf .preview__body,
.preview--text .preview__body {
  align-items: stretch;
  justify-items: stretch;
  padding: 0;
}

.preview__media--image {
  max-width: 100%;
  max-height: min(78vh, 820px);
  border-radius: var(--radius-md);
  background: #000;
  object-fit: contain;
}

.preview__media--video,
.preview__media--pdf {
  width: 100%;
  height: 100%;
  border: 0;
  border-radius: 0;
  background: #000;
}

.preview__media--video {
  object-fit: contain;
}

.preview__media--pdf {
  background: var(--color-surface);
}

.preview__audio {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space4);
  width: min(400px, 100%);
  padding: var(--space8) var(--space4);
  color: var(--color-text-primary);
}

.preview__audio-art {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  border-radius: 18px;
  background: color-mix(in srgb, var(--color-brand-violet) 18%, var(--color-surface-secondary));
  color: var(--color-brand-violet);
}

.preview__audio-name {
  margin: 0;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-label-size);
  font-weight: 600;
}

.preview__media--audio {
  width: 100%;
}

.preview__text {
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  margin: 0;
  padding: var(--space4) var(--space5);
  overflow: auto;
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.preview__hint {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--font-caption-size);
}

.preview__retry {
  margin-top: var(--space3);
  min-height: 34px;
  padding: 0 14px;
  border-radius: 10px;
  background: var(--color-primary);
  color: var(--color-on-primary);
  font-size: 13px;
  font-weight: 600;
}

.preview--video .preview__hint {
  color: rgb(244 246 251 / 0.7);
}

.preview__hint.is-error {
  color: var(--color-danger);
}

@media (max-width: 720px) {
  .preview__tool span {
    display: none;
  }
}

@media (max-width: 900px) {
  .drive__col-type,
  .drive__col-size {
    display: none;
  }

  .drive__name {
    max-width: 58vw;
  }
}
</style>

