<script setup lang="ts">
// 站点 JSON 导入：流程对齐 MoviePilot SiteImportDialog（选文件 → 预览 → 逐条导入 → 结果）。
import { ref, watch } from 'vue'

import { useNotifyStore } from '@/application/notify'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import { describeError } from '@/core/api/error'
import { sitesApi } from '@/data/api'

const open = defineModel<boolean>('open', { required: true })
const emit = defineEmits<{ success: [] }>()

const notify = useNotifyStore()

type Stage = 'select' | 'preview' | 'importing' | 'done'

const stage = ref<Stage>('select')
const dragging = ref(false)
const selectedName = ref('')
const importData = ref<Record<string, unknown>[]>([])
const previewData = ref<Record<string, unknown>[]>([])
const progress = ref(0)
const successes = ref<string[]>([])
const errors = ref<{ name: string; error: string }[]>([])
const fileInput = ref<HTMLInputElement | null>(null)

function siteName(raw: Record<string, unknown>): string {
  return String(raw.name || raw.domain || '未命名站点')
}

function siteUrl(raw: Record<string, unknown>): string {
  return String(raw.url || '')
}

function isValid(raw: Record<string, unknown>): boolean {
  return Boolean(raw.name && (raw.domain || raw.url) && raw.url)
}

function reset(): void {
  stage.value = 'select'
  dragging.value = false
  selectedName.value = ''
  importData.value = []
  previewData.value = []
  progress.value = 0
  successes.value = []
  errors.value = []
  if (fileInput.value) fileInput.value.value = ''
}

function close(done = false): void {
  if (done) emit('success')
  open.value = false
}

async function processFile(file: File): Promise<void> {
  if (!file.name.toLowerCase().endsWith('.json') && file.type !== 'application/json') {
    notify.failure('请选择 JSON 文件')
    return
  }
  try {
    const text = await file.text()
    const data = JSON.parse(text) as unknown
    if (!Array.isArray(data)) {
      notify.failure('文件格式无效：需要站点数组')
      return
    }
    const rows = data.filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    importData.value = rows
    previewData.value = rows.slice(0, 5)
    selectedName.value = file.name
    stage.value = 'preview'
  } catch {
    notify.failure('无法解析该 JSON 文件')
  }
}

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) void processFile(file)
}

function onDrop(event: DragEvent): void {
  event.preventDefault()
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) void processFile(file)
}

async function startImport(): Promise<void> {
  const valid = importData.value.filter(isValid)
  if (!valid.length) {
    notify.failure('没有可导入的有效站点（需要 name、url）')
    return
  }
  if (valid.length !== importData.value.length) {
    notify.notify(`将导入 ${valid.length}/${importData.value.length} 条有效数据`, { tone: 'warning' })
  }

  stage.value = 'importing'
  progress.value = 0
  successes.value = []
  errors.value = []

  for (let i = 0; i < valid.length; i += 1) {
    const site = valid[i]
    const raw = { ...site }
    delete raw.id
    try {
      await sitesApi.importOne(raw)
      successes.value.push(siteName(site))
    } catch (error) {
      errors.value.push({ name: siteName(site), error: describeError(error) })
    }
    progress.value = Math.round(((i + 1) / valid.length) * 100)
  }

  stage.value = 'done'
  if (!errors.value.length && successes.value.length) {
    notify.success(`成功导入 ${successes.value.length} 个站点`)
    close(true)
    return
  }
  if (!successes.value.length) {
    notify.failure(`导入失败，${errors.value.length} 个站点均未成功`)
    return
  }
  notify.notify(`导入完成：成功 ${successes.value.length}，失败 ${errors.value.length}`, {
    tone: 'warning',
  })
}

watch(open, (value) => {
  if (value) reset()
})
</script>

<template>
  <AppDialog :open="open" title="导入站点" size="md" @update:open="open = $event">
    <div class="import">
      <template v-if="stage === 'select'">
        <div
          class="import__drop"
          :class="{ 'is-dragging': dragging }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop="onDrop"
        >
          <AppIcon name="download" :size="28" />
          <p class="import__title">拖拽 JSON 文件到此处</p>
          <p class="import__hint">支持 MoviePilot 导出的站点数组（.json）</p>
          <AppButton size="sm" variant="secondary" @click="fileInput?.click()">选择文件</AppButton>
          <input
            ref="fileInput"
            class="import__file"
            type="file"
            accept=".json,application/json"
            @change="onFileChange"
          />
        </div>
      </template>

      <template v-else-if="stage === 'preview'">
        <p class="import__meta">
          文件「{{ selectedName }}」共 {{ importData.length }} 个站点，预览前
          {{ previewData.length }} 条。
        </p>
        <ul class="import__list">
          <li
            v-for="(site, index) in previewData"
            :key="index"
            class="import__item"
            :class="{ 'is-invalid': !isValid(site) }"
          >
            <AppIcon :name="isValid(site) ? 'check' : 'alert'" :size="16" />
            <div class="import__item-main">
              <span class="import__item-name">{{ siteName(site) }}</span>
              <span class="import__item-url">{{ siteUrl(site) || '缺少地址' }}</span>
            </div>
            <span v-if="!isValid(site)" class="import__badge">无效</span>
          </li>
        </ul>
      </template>

      <template v-else-if="stage === 'importing'">
        <p class="import__meta">正在导入… {{ progress }}%</p>
        <div class="import__bar" aria-hidden="true">
          <span class="import__bar-fill" :style="{ width: `${progress}%` }" />
        </div>
      </template>

      <template v-else>
        <p v-if="successes.length" class="import__ok">成功 {{ successes.length }} 个</p>
        <div v-if="errors.length" class="import__errors">
          <p class="import__fail">失败 {{ errors.length }} 个</p>
          <ul class="import__list">
            <li v-for="(item, index) in errors" :key="index" class="import__item is-invalid">
              <AppIcon name="alert" :size="16" />
              <div class="import__item-main">
                <span class="import__item-name">{{ item.name }}</span>
                <span class="import__item-url">{{ item.error }}</span>
              </div>
            </li>
          </ul>
        </div>
      </template>
    </div>

    <template #footer>
      <template v-if="stage === 'preview'">
        <AppButton size="sm" @click="reset">重选文件</AppButton>
        <AppButton size="sm" variant="primary" :disabled="!importData.length" @click="startImport">
          开始导入
        </AppButton>
      </template>
      <template v-else-if="stage === 'done'">
        <AppButton size="sm" @click="reset">继续导入</AppButton>
        <AppButton size="sm" variant="primary" @click="close(successes.length > 0)">完成</AppButton>
      </template>
      <template v-else-if="stage === 'select'">
        <AppButton size="sm" @click="close(false)">取消</AppButton>
      </template>
    </template>
  </AppDialog>
</template>

<style scoped>
.import {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.import__drop {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space2);
  padding: var(--space8) var(--space4);
  border: 1px dashed var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  text-align: center;
  transition:
    border-color var(--duration-micro) ease,
    background-color var(--duration-micro) ease;
}

.import__drop.is-dragging {
  border-color: color-mix(in srgb, var(--color-primary) 55%, var(--panel-border));
  background: color-mix(in srgb, var(--color-primary-subtle) 70%, var(--color-surface-secondary));
  color: var(--color-primary);
}

.import__title {
  margin: 0;
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.import__hint {
  margin: 0 0 var(--space2);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.import__file {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.import__meta,
.import__ok,
.import__fail {
  margin: 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.import__ok {
  color: var(--color-success);
}

.import__fail {
  color: var(--color-danger);
  margin-bottom: var(--space2);
}

.import__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  overflow: hidden;
}

.import__item {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-height: 44px;
  padding: 8px 12px;
  color: var(--color-success);
}

.import__item + .import__item {
  border-top: 1px solid var(--panel-divider);
}

.import__item.is-invalid {
  color: var(--color-danger);
}

.import__item-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.import__item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.import__item-url {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.import__badge {
  flex: none;
  font-size: 12px;
  color: var(--color-danger);
}

.import__bar {
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  overflow: hidden;
}

.import__bar-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-primary);
  transition: width var(--duration-page) ease;
}
</style>
