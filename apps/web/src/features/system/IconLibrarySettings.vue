<script setup lang="ts">
// 图标库（设定 · 图标库）：海报缺失时按顺序在图标库中匹配。
// 整表提交——任何一处改动都发完整列表，避免并发下顺序错乱。
// 添加 / 编辑 / 删除一律弹窗，不在列表里展开表单，避免撑破分组卡。
import { computed, onMounted, ref } from 'vue'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'
import { describeError } from '@/core/api/error'
import { preferencesApi } from '@/data/api'
import type { IconLibrary, Preferences } from '@/domain/contract'

const preferences = ref<Preferences | null>(null)
const loading = ref(true)
const errorText = ref('')

const iconLibraries = computed(() => preferences.value?.iconLibraries ?? [])
const savingIcon = ref(false)
const iconError = ref('')
const editorOpen = ref(false)
const deleteOpen = ref(false)
const pendingDelete = ref<IconLibrary | null>(null)
const iconDraft = ref<{ id: string | null; name: string; url: string }>({
  id: null,
  name: '',
  url: '',
})

const editorTitle = computed(() => (iconDraft.value.id ? '编辑图标库' : '添加图标库'))

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    preferences.value = await preferencesApi.get()
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

function resetIconDraft(): void {
  iconDraft.value = { id: null, name: '', url: '' }
  iconError.value = ''
}

function openCreate(): void {
  resetIconDraft()
  editorOpen.value = true
}

function editIconLibrary(library: IconLibrary): void {
  iconDraft.value = { id: library.id, name: library.name, url: library.url }
  iconError.value = ''
  editorOpen.value = true
}

function askDelete(library: IconLibrary): void {
  pendingDelete.value = library
  deleteOpen.value = true
}

async function persistIconLibraries(next: IconLibrary[], failure: string): Promise<boolean> {
  savingIcon.value = true
  iconError.value = ''
  try {
    preferences.value = await preferencesApi.saveIconLibraries(next)
    return true
  } catch (error) {
    iconError.value = `${failure}：${describeError(error)}`
    return false
  } finally {
    savingIcon.value = false
  }
}

async function submitIconLibrary(): Promise<void> {
  const name = iconDraft.value.name.trim()
  const url = iconDraft.value.url.trim()
  if (!name || !url) {
    iconError.value = '请填写名称与 JSON 地址'
    return
  }
  const editingId = iconDraft.value.id
  const next = editingId
    ? iconLibraries.value.map((item) => (item.id === editingId ? { ...item, name, url } : item))
    : [...iconLibraries.value, { id: '', name, url, enabled: true }]
  if (await persistIconLibraries(next, editingId ? '保存失败' : '添加失败')) {
    editorOpen.value = false
    resetIconDraft()
  }
}

async function confirmDelete(): Promise<void> {
  const target = pendingDelete.value
  if (!target) return
  const next = iconLibraries.value.filter((item) => item.id !== target.id)
  if (await persistIconLibraries(next, '删除失败')) {
    deleteOpen.value = false
    pendingDelete.value = null
    if (iconDraft.value.id === target.id) resetIconDraft()
  }
}

async function toggleIconLibrary(id: string): Promise<void> {
  const next = iconLibraries.value.map((item) =>
    item.id === id ? { ...item, enabled: !item.enabled } : item,
  )
  await persistIconLibraries(next, '切换失败')
}

async function moveIconLibrary(index: number, offset: number): Promise<void> {
  const next = [...iconLibraries.value]
  const target = index + offset
  if (target < 0 || target >= next.length) return
  const current = next[index]
  next[index] = next[target]
  next[target] = current
  await persistIconLibraries(next, '调整顺序失败')
}

onMounted(() => void load())
</script>

<template>
  <AppErrorState v-if="errorText" :message="errorText" @retry="load" />

  <SysStyles v-else>
    <section class="group">
      <div class="card">
        <header class="card__head">
          <div class="card__head-main">
            <h2 class="card__title">图标库</h2>
            <p class="card__desc">
              海报缺失时按列表顺序匹配 JSON 图标索引；关闭或删除后不再参与。
            </p>
          </div>
          <button
            type="button"
            class="card__action"
            :disabled="savingIcon"
            @click="openCreate"
          >
            <AppIcon name="image" :size="14" />添加图标库
          </button>
        </header>

        <div v-if="loading" class="card__body">
          <div class="skel">
            <AppSkeleton height="52px" width="100%" />
            <AppSkeleton height="52px" width="100%" />
          </div>
        </div>

        <div v-else-if="!iconLibraries.length" class="card__body card__body--empty">
          <div class="empty">
            <span class="empty__icon" aria-hidden="true">
              <AppIcon name="image" :size="22" />
            </span>
            <p class="empty__title">还没有图标库</p>
            <p class="empty__desc">添加一个 JSON 索引后，海报缺失时会按顺序在此匹配。</p>
            <AppButton size="sm" variant="primary" :disabled="savingIcon" @click="openCreate">
              添加图标库
            </AppButton>
          </div>
        </div>

        <div v-else class="card__body card__body--list">
          <p v-if="iconError && !editorOpen && !deleteOpen" class="list-error">{{ iconError }}</p>

          <ul class="libs" aria-label="图标库列表">
            <li
              v-for="(library, index) in iconLibraries"
              :key="library.id"
              class="lib"
              :class="{ 'is-off': !library.enabled }"
            >
              <span class="lib__rank" :title="`匹配优先级第 ${index + 1}`">{{ index + 1 }}</span>

              <div class="lib__main">
                <div class="lib__title-row">
                  <span class="lib__name">{{ library.name }}</span>
                  <span class="chip" :class="{ 'is-off': !library.enabled }">
                    {{ library.enabled ? '已启用' : '已关闭' }}
                  </span>
                </div>
                <a
                  class="lib__url"
                  :href="library.url"
                  :title="library.url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ library.url }}
                </a>
              </div>

              <div class="lib__actions">
                <div class="lib__order" role="group" aria-label="调整匹配顺序">
                  <button
                    type="button"
                    class="icon-btn"
                    :disabled="index === 0 || savingIcon"
                    title="上移，提高匹配优先级"
                    aria-label="上移"
                    @click="moveIconLibrary(index, -1)"
                  >
                    <AppIcon name="chevron-down" :size="14" class="icon-btn__up" />
                  </button>
                  <button
                    type="button"
                    class="icon-btn"
                    :disabled="index === iconLibraries.length - 1 || savingIcon"
                    title="下移，降低匹配优先级"
                    aria-label="下移"
                    @click="moveIconLibrary(index, 1)"
                  >
                    <AppIcon name="chevron-down" :size="14" />
                  </button>
                </div>

                <AppButton size="sm" :disabled="savingIcon" @click="editIconLibrary(library)">
                  编辑
                </AppButton>
                <AppButton size="sm" :disabled="savingIcon" @click="askDelete(library)">
                  删除
                </AppButton>

                <label class="switch" :title="library.enabled ? '关闭后不再匹配' : '启用后参与匹配'">
                  <input
                    type="checkbox"
                    :checked="library.enabled"
                    :disabled="savingIcon"
                    :aria-label="`${library.name} ${library.enabled ? '已启用' : '已关闭'}`"
                    @change="toggleIconLibrary(library.id)"
                  />
                  <span class="switch__track" aria-hidden="true" />
                </label>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <AppDialog
      v-model:open="editorOpen"
      :title="editorTitle"
      description="名称用于展示，JSON 地址需可公开访问。"
      size="sm"
    >
      <div class="editor">
        <label class="field">
          <span class="field__label">名称</span>
          <input
            v-model="iconDraft.name"
            class="field__input"
            type="text"
            placeholder="例如 白糖圆形图标库"
          />
        </label>
        <label class="field">
          <span class="field__label">JSON 地址</span>
          <input
            v-model="iconDraft.url"
            class="field__input"
            type="url"
            placeholder="粘贴图标库的 JSON 地址"
          />
        </label>
        <p v-if="iconError" class="row__error">{{ iconError }}</p>
      </div>
      <template #footer>
        <AppButton size="sm" @click="editorOpen = false">取消</AppButton>
        <AppButton
          size="sm"
          variant="primary"
          :loading="savingIcon"
          :disabled="!iconDraft.name.trim() || !iconDraft.url.trim()"
          @click="submitIconLibrary"
        >
          {{ iconDraft.id ? '保存' : '添加' }}
        </AppButton>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="deleteOpen"
      title="删除图标库？"
      :description="pendingDelete ? `将移除「${pendingDelete.name}」，海报匹配不再使用它。` : ''"
      tone="danger"
      size="sm"
    >
      <p v-if="iconError" class="row__error">{{ iconError }}</p>
      <template #footer>
        <AppButton size="sm" @click="deleteOpen = false">取消</AppButton>
        <AppButton size="sm" variant="danger" :loading="savingIcon" @click="confirmDelete">
          确认删除
        </AppButton>
      </template>
    </AppDialog>
  </SysStyles>
</template>

<style scoped>
.card__body--list {
  gap: 0;
  padding: 0;
}

.card__body--empty {
  padding-block: var(--space8);
}

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space2);
  text-align: center;
}

.empty__icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin-bottom: var(--space1);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.empty__title {
  margin: 0;
  font-size: var(--font-label-size);
  font-weight: 600;
  color: var(--color-text-primary);
}

.empty__desc {
  margin: 0 0 var(--space2);
  max-width: 44ch;
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.skel {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.list-error {
  margin: 0;
  padding: var(--space3) var(--space6);
  border-bottom: 1px solid var(--panel-divider);
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.libs {
  list-style: none;
  margin: 0;
  padding: 0;
}

.lib {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space3);
  min-height: 64px;
  padding: var(--space3) var(--space6);
  border-top: 1px solid var(--panel-divider);
  transition: background-color var(--duration-micro) ease;
}

.lib:first-child {
  border-top: 0;
}

.lib:hover {
  background: color-mix(in srgb, var(--color-surface-secondary) 55%, transparent);
}

.lib.is-off .lib__name {
  color: var(--color-text-secondary);
}

.lib__rank {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
  line-height: 1;
}

.lib__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lib__title-row {
  display: flex;
  align-items: center;
  gap: var(--space2);
  min-width: 0;
}

.lib__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
  line-height: 1.3;
}

.lib__url {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  text-decoration: none;
  line-height: 1.4;
}

.lib__url:hover {
  color: var(--color-text-primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.lib__actions {
  flex: none;
  display: flex;
  align-items: center;
  gap: var(--space2);
}

.lib__order {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.icon-btn:hover:not(:disabled) {
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.icon-btn:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}

.icon-btn__up {
  transform: rotate(180deg);
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

.editor {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

.row__error {
  margin: 0;
}

@media (max-width: 900px) {
  .lib {
    grid-template-columns: auto minmax(0, 1fr);
    padding-left: var(--space4);
    padding-right: var(--space4);
  }

  .lib__actions {
    grid-column: 2;
    justify-content: flex-end;
  }

  .list-error {
    padding-left: var(--space4);
    padding-right: var(--space4);
  }
}
</style>
