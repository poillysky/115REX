// 影视库控制器：列表、详情、目录、继续观看。

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { libraryApi } from '@/data/api'
import { describeError } from '@/core/api/error'
import type { DirEntry, MediaItem, MediaItemDetail } from '@/domain/contract'

export const useLibraryStore = defineStore('library', () => {
  const items = ref<MediaItem[]>([])
  const nextCursor = ref<string | null>(null)
  const continueItems = ref<MediaItem[]>([])
  const detail = ref<MediaItemDetail | null>(null)
  const sort = ref<'recent' | 'title'>('recent')
  const filter = ref('')
  const loading = ref(false)
  const errorText = ref('')

  async function load(reset = true): Promise<void> {
    loading.value = true
    errorText.value = ''
    try {
      const response = await libraryApi.items({
        sort: sort.value,
        q: filter.value || undefined,
        cursor: reset ? undefined : (nextCursor.value ?? undefined),
      })
      items.value = reset ? response.items : [...items.value, ...response.items]
      nextCursor.value = response.nextCursor
    } catch (error) {
      errorText.value = describeError(error)
    } finally {
      loading.value = false
    }
  }

  async function loadContinue(): Promise<void> {
    try {
      const response = await libraryApi.continueWatching()
      continueItems.value = response.items
    } catch {
      continueItems.value = []
    }
  }

  async function loadDetail(id: string): Promise<MediaItemDetail | null> {
    loading.value = true
    errorText.value = ''
    try {
      detail.value = await libraryApi.item(id)
      return detail.value
    } catch (error) {
      errorText.value = describeError(error)
      detail.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  async function toggleFavorite(id: string, favorite: boolean): Promise<void> {
    const response = await libraryApi.putFavorite(id, favorite)
    if (detail.value?.id === id) detail.value.favorite = response.favorite
    const found = items.value.find((item) => item.id === id)
    if (found) found.favorite = response.favorite
  }

  async function loadDirs(path: string | null): Promise<DirEntry[]> {
    const response = await libraryApi.dirs(path)
    return response.entries
  }

  return {
    items,
    nextCursor,
    continueItems,
    detail,
    sort,
    filter,
    loading,
    errorText,
    load,
    loadContinue,
    loadDetail,
    toggleFavorite,
    loadDirs,
  }
})
