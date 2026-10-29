<script setup lang="ts">
// 从图标库挑头像（docs/03 §3）：图标库是用户在「设定 · 图标库」里维护的 JSON 索引，
// 这里按库切换、按名称筛选，选中后把图片地址交回账号页。
import { computed, onMounted, ref, watch } from 'vue'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import { describeError } from '@/core/api/error'
import { preferencesApi } from '@/data/api'
import type { IconLibrary } from '@/domain/contract'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{
  'update:open': [value: boolean]
  pick: [url: string]
}>()

interface Entry {
  name: string
  url: string
}

const libraries = ref<IconLibrary[]>([])
const activeId = ref('')
const entries = ref<Entry[]>([])
const loading = ref(false)
const errorText = ref('')
const query = ref('')

let requestToken = 0

const activeLibrary = computed(() => libraries.value.find((item) => item.id === activeId.value))

const filtered = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return entries.value
  return entries.value.filter((item) => item.name.toLowerCase().includes(keyword))
})

async function loadLibraries(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const preferences = await preferencesApi.get()
    libraries.value = preferences.iconLibraries.filter((item) => item.enabled)
    if (!libraries.value.some((item) => item.id === activeId.value)) {
      activeId.value = libraries.value[0]?.id ?? ''
    }
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

async function loadEntries(): Promise<void> {
  const library = activeLibrary.value
  if (!library) {
    entries.value = []
    return
  }
  const token = (requestToken += 1)
  loading.value = true
  errorText.value = ''
  try {
    const list = await preferencesApi.iconLibraryIcons(library.url)
    // 快速切换图标库时丢弃过期响应
    if (token === requestToken) entries.value = list
  } catch (error) {
    if (token === requestToken) {
      entries.value = []
      errorText.value = describeError(error)
    }
  } finally {
    if (token === requestToken) loading.value = false
  }
}

function choose(url: string): void {
  emit('pick', url)
  emit('update:open', false)
}

watch(
  () => props.open,
  (open) => {
    if (!open) return
    query.value = ''
    if (!libraries.value.length) void loadLibraries()
    else void loadEntries()
  },
)

watch(activeId, () => {
  if (props.open) void loadEntries()
})

onMounted(() => {
  if (props.open) void loadLibraries()
})
</script>

<template>
  <AppDialog
    :open="open"
    title="从图标库选择头像"
    description="图标库在「设定 · 图标库」中维护，这里只列出已启用的库。"
    size="md"
    @update:open="emit('update:open', $event)"
  >
    <div class="picker">
      <div v-if="libraries.length" class="picker__tabs" role="tablist" aria-label="图标库">
        <button
          v-for="library in libraries"
          :key="library.id"
          type="button"
          role="tab"
          class="picker__tab"
          :class="{ 'is-active': library.id === activeId }"
          :aria-selected="library.id === activeId"
          @click="activeId = library.id"
        >
          {{ library.name }}
        </button>
      </div>

      <label class="field">
        <span class="field__label">筛选</span>
        <input
          v-model="query"
          class="field__input"
          type="search"
          placeholder="输入图标名称，例如 bilibili"
          autocomplete="off"
        />
      </label>

      <p v-if="errorText" class="picker__error">{{ errorText }}</p>

      <div v-if="loading" class="picker__grid">
        <AppSkeleton v-for="n in 12" :key="n" height="56px" />
      </div>

      <p v-else-if="!libraries.length" class="picker__empty">
        还没有启用的图标库，先到「设定 · 图标库」添加或启用一个。
      </p>

      <p v-else-if="!filtered.length" class="picker__empty">
        {{ query ? '没有匹配的图标，换个关键词试试。' : '这个图标库没有可用条目。' }}
      </p>

      <div v-else class="picker__grid">
        <button
          v-for="entry in filtered"
          :key="entry.url"
          type="button"
          class="icon-cell"
          :title="entry.name"
          @click="choose(entry.url)"
        >
          <img :src="entry.url" :alt="entry.name" loading="lazy" />
          <span class="icon-cell__name">{{ entry.name }}</span>
        </button>
      </div>
    </div>

    <template #footer>
      <span class="picker__count">
        <AppIcon name="image" :size="15" />
        共 {{ filtered.length }} 个
      </span>
      <AppButton size="sm" @click="emit('update:open', false)">取消</AppButton>
    </template>
  </AppDialog>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

/* 库切换：一层浅底上的文字标签，选中用主文字色 + 白面，不做品牌色块 */
.picker__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space1);
  padding: var(--space1);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.picker__tab {
  height: 30px;
  padding: 0 var(--space3);
  border-radius: var(--radius-sm);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.picker__tab:hover {
  color: var(--color-text-primary);
}

.picker__tab.is-active {
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-weight: var(--font-label-weight);
}

.picker__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(88px, 1fr));
  gap: var(--space2);
  max-height: 320px;
  overflow-y: auto;
  padding-right: var(--space1);
}

.icon-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space1);
  padding: var(--space2) var(--space1);
  border-radius: var(--radius-md);
  transition: background-color var(--duration-micro) ease;
}

.icon-cell:hover,
.icon-cell:focus-visible {
  background: var(--color-surface-secondary);
}

.icon-cell img {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-md);
  object-fit: contain;
  background: var(--color-surface-secondary);
}

.icon-cell__name {
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  text-align: center;
}

.picker__empty,
.picker__error {
  padding: var(--space5) 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  text-align: center;
}

.picker__error {
  color: var(--color-danger);
}

.picker__count {
  display: inline-flex;
  align-items: center;
  gap: var(--space1);
  margin-right: auto;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

@media (max-width: 640px) {
  .picker__grid {
    grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
    max-height: 46vh;
  }
}
</style>
