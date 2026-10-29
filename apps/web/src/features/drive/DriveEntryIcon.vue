<script setup lang="ts">
// 网盘列表彩色文件图标：文件夹黄 / 云下载橙 / 按扩展名区分类型色。
import { computed } from 'vue'

import type { DriveEntry } from '@/domain/contract'

const props = withDefaults(defineProps<{ entry: DriveEntry; size?: number }>(), { size: 28 })

type Kind =
  | 'folder'
  | 'cloud'
  | 'video'
  | 'audio'
  | 'image'
  | 'archive'
  | 'doc'
  | 'subtitle'
  | 'file'

const VIDEO = new Set(['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'ts', 'm2ts', 'webm', 'rmvb'])
const AUDIO = new Set(['mp3', 'flac', 'aac', 'wav', 'm4a', 'ogg', 'wma', 'ape'])
const IMAGE = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'svg', 'ico'])
const ARCHIVE = new Set(['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'iso'])
const DOC = new Set(['pdf', 'doc', 'docx', 'txt', 'md', 'xls', 'xlsx', 'ppt', 'pptx', 'csv'])
const SUB = new Set(['srt', 'ass', 'ssa', 'vtt', 'sup'])

const kind = computed<Kind>(() => {
  if (props.entry.isDir) {
    const name = props.entry.name
    if (/云下载|offline|download/i.test(name)) return 'cloud'
    return 'folder'
  }
  const ext = (props.entry.extension || '').toLowerCase().replace(/^\./, '')
  if (VIDEO.has(ext)) return 'video'
  if (AUDIO.has(ext)) return 'audio'
  if (IMAGE.has(ext)) return 'image'
  if (ARCHIVE.has(ext)) return 'archive'
  if (DOC.has(ext)) return 'doc'
  if (SUB.has(ext)) return 'subtitle'
  return 'file'
})

const thumbUrl = computed(() => {
  const url = (props.entry.thumbUrl || '').trim()
  return url || ''
})
</script>

<template>
  <span
    class="ficon"
    :class="[`ficon--${kind}`, { 'ficon--thumb': !!thumbUrl }]"
    :style="{ width: `${size}px`, height: `${size}px` }"
    aria-hidden="true"
  >
    <img v-if="thumbUrl" class="ficon__thumb" :src="thumbUrl" alt="" loading="lazy" decoding="async" />

    <!-- 黄文件夹 -->
    <svg v-else-if="kind === 'folder'" viewBox="0 0 32 32" fill="none">
      <path
        d="M4 9.5A2.5 2.5 0 0 1 6.5 7h5.2c.5 0 1 .2 1.3.6l1.2 1.4c.3.4.8.6 1.3.6H25.5A2.5 2.5 0 0 1 28 12v12.5a2.5 2.5 0 0 1-2.5 2.5h-19A2.5 2.5 0 0 1 4 24.5v-15Z"
        fill="var(--ficon-folder-body)"
      />
      <path
        d="M4 13h24v11.5A2.5 2.5 0 0 1 25.5 27h-19A2.5 2.5 0 0 1 4 24.5V13Z"
        fill="var(--ficon-folder-front)"
      />
    </svg>

    <!-- 云下载：与黄文件夹同视觉外框（约 24×24） -->
    <svg v-else-if="kind === 'cloud'" viewBox="0 0 32 32" fill="none">
      <rect x="4" y="5" width="24" height="22" rx="5" fill="var(--ficon-cloud-bg)" />
      <path
        d="M11.2 20.2h10c1.65 0 2.9-1.3 2.9-2.8 0-1.4-1.05-2.55-2.45-2.7-.25-2-2-3.5-4.1-3.5-1.5 0-2.8.8-3.55 1.95-.35-.2-.75-.3-1.2-.3-1.5 0-2.7 1.15-2.7 2.6 0 .15 0 .35.05.5-1.2.35-2.1 1.4-2.1 2.65 0 1.5 1.2 2.6 2.7 2.6h.45Z"
        fill="#fff"
      />
    </svg>

    <!-- 视频 -->
    <svg v-else-if="kind === 'video'" viewBox="0 0 32 32" fill="none">
      <rect x="3" y="6" width="26" height="20" rx="4" fill="var(--ficon-video)" />
      <path d="M13.5 12.2v7.6L20.2 16l-6.7-3.8Z" fill="#fff" />
    </svg>

    <!-- 音频 -->
    <svg v-else-if="kind === 'audio'" viewBox="0 0 32 32" fill="none">
      <rect x="3" y="3" width="26" height="26" rx="6" fill="var(--ficon-audio)" />
      <circle cx="12" cy="18.8" r="2.4" fill="#fff" />
      <circle cx="21" cy="17" r="2.4" fill="#fff" />
      <path d="M14.4 18.8V10.2l8.6-1.7v8.5" stroke="#fff" stroke-width="1.8" fill="none" />
    </svg>

    <!-- 图片 -->
    <svg v-else-if="kind === 'image'" viewBox="0 0 32 32" fill="none">
      <rect x="3" y="5" width="26" height="22" rx="4" fill="var(--ficon-image)" />
      <circle cx="11.5" cy="12.5" r="2.2" fill="#fff" />
      <path d="M6.5 23.5 13 16l4.2 4.5 3.3-3.8 5 6.8H6.5Z" fill="#fff" opacity=".92" />
    </svg>

    <!-- 压缩包 -->
    <svg v-else-if="kind === 'archive'" viewBox="0 0 32 32" fill="none">
      <path
        d="M7 5.5h12l6 6V26a2.5 2.5 0 0 1-2.5 2.5h-15A2.5 2.5 0 0 1 5 26V8A2.5 2.5 0 0 1 7.5 5.5H7Z"
        fill="var(--ficon-archive)"
      />
      <path d="M19 5.5V12h6L19 5.5Z" fill="#fff" opacity=".35" />
      <path
        d="M14.2 8h3.6v2.2h-3.6V8Zm0 3.4h3.6v2.2h-3.6v-2.2Zm0 3.4h3.6v2.2h-3.6v-2.2Zm-1 3.6h5.6v6.2h-5.6v-6.2Z"
        fill="#fff"
      />
    </svg>

    <!-- 文档 -->
    <svg v-else-if="kind === 'doc'" viewBox="0 0 32 32" fill="none">
      <path
        d="M8 4.5h10l6 6V26a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 6 26V7A2.5 2.5 0 0 1 8.5 4.5H8Z"
        fill="var(--ficon-doc)"
      />
      <path d="M18 4.5V11h6L18 4.5Z" fill="#fff" opacity=".35" />
      <path d="M10 15h12v1.8H10V15Zm0 4h12v1.8H10V19Zm0 4h8v1.8h-8V23Z" fill="#fff" />
    </svg>

    <!-- 字幕 -->
    <svg v-else-if="kind === 'subtitle'" viewBox="0 0 32 32" fill="none">
      <rect x="3" y="7" width="26" height="18" rx="4" fill="var(--ficon-subtitle)" />
      <path d="M8 18.5h7V20H8v-1.5Zm9 0h7V20h-7v-1.5ZM8 14h16v1.5H8V14Z" fill="#fff" />
    </svg>

    <!-- 默认文件 -->
    <svg v-else viewBox="0 0 32 32" fill="none">
      <path
        d="M8 4.5h10l6 6V26a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 6 26V7A2.5 2.5 0 0 1 8.5 4.5H8Z"
        fill="var(--ficon-file)"
      />
      <path d="M18 4.5V11h6L18 4.5Z" fill="#fff" opacity=".4" />
    </svg>
  </span>
</template>

<style scoped>
.ficon {
  /* 文件类型色：仅网盘列表语义，不进全局 token */
  --ficon-folder-body: #ffc107;
  --ficon-folder-front: #ffca28;
  --ficon-cloud-bg: #ff8a3d;
  --ficon-video: #5b8cff;
  --ficon-audio: #a78bfa;
  --ficon-image: #34c759;
  --ficon-archive: #f0a020;
  --ficon-doc: #3b82f6;
  --ficon-subtitle: #64748b;
  --ficon-file: #94a3b8;

  flex: none;
  display: inline-grid;
  place-items: center;
  line-height: 0;
  overflow: hidden;
  border-radius: 4px;
}

.ficon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.ficon__thumb {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  background: var(--color-surface-secondary);
}

:global([data-theme='dark']) .ficon {
  --ficon-folder-body: #e6b008;
  --ficon-folder-front: #f5c518;
  --ficon-cloud-bg: #f08a45;
  --ficon-video: #6b9aff;
  --ficon-audio: #b49afc;
  --ficon-image: #3dd68c;
  --ficon-archive: #f0ae3a;
  --ficon-doc: #5b9bff;
  --ficon-subtitle: #8b98a8;
  --ficon-file: #8b97a8;
}
</style>
