<script setup lang="ts">
// 条目详情（docs/03 §3、docs/02 §11 详情页）：
// 海报 + 元数据 + 音轨/字幕分区；播放为主操作，收藏为次操作。
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppArtwork from '@/features/shell/components/AppArtwork.vue'
import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import { formatBytes, formatDate, formatDuration, progressRatio } from '@/domain/format'
import { describeError } from '@/core/api/error'
import { useLibraryStore } from '@/application/library'
import { useSessionStore } from '@/application/session'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()
const session = useSessionStore()

const favoriteBusy = ref(false)
const favoriteError = ref('')

const id = computed(() => String(route.params.id))
const item = computed(() => (library.detail?.id === id.value ? library.detail : null))
const canPlay = computed(() => session.capabilities.play)

async function load(): Promise<void> {
  await library.loadDetail(id.value)
}

async function toggleFavorite(): Promise<void> {
  if (!item.value) return
  favoriteBusy.value = true
  favoriteError.value = ''
  try {
    await library.toggleFavorite(item.value.id, !item.value.favorite)
  } catch (error) {
    favoriteError.value = describeError(error)
  } finally {
    favoriteBusy.value = false
  }
}

watch(id, () => void load(), { immediate: true })
</script>

<template>
  <div class="detail">
    <button type="button" class="detail__back" @click="router.back()">
      <AppIcon name="chevron-left" :size="18" />
      返回
    </button>

    <AppErrorState v-if="library.errorText" :message="library.errorText" @retry="load" />

    <div v-else-if="library.loading && !item" class="detail__skeleton">
      <AppSkeleton height="0" style="aspect-ratio: 2 / 3; height: auto" radius="var(--radius-xl)" />
      <div class="detail__skeleton-body">
        <AppSkeleton height="30px" width="60%" />
        <AppSkeleton height="16px" width="40%" />
        <AppSkeleton height="88px" radius="var(--radius-lg)" />
      </div>
    </div>

    <AppEmptyState
      v-else-if="!item"
      title="条目不存在"
      description="可能已被删除，回到影视库刷新列表"
      icon="film"
    >
      <AppButton size="sm" @click="router.push({ name: 'discover-movie' })">回到影视库</AppButton>
    </AppEmptyState>

    <template v-else>
      <section class="hero">
        <AppArtwork :src="item.posterUrl" :alt="item.title" radius="var(--radius-xl)" />

        <div class="hero__body">
          <h1 class="hero__title">{{ item.title }}</h1>
          <p v-if="item.originalTitle" class="hero__original">{{ item.originalTitle }}</p>

          <div class="hero__meta tabular">
            <span>{{ item.year ?? '年份未知' }}</span>
            <span>·</span>
            <span>{{ item.resolution ?? '画质未知' }}</span>
            <span>·</span>
            <span>{{ formatBytes(item.sizeBytes) }}</span>
            <span>·</span>
            <span>{{ formatDuration(item.durationSeconds) }}</span>
          </div>

          <p v-if="item.overview" class="hero__overview">{{ item.overview }}</p>

          <div v-if="item.progressSeconds > 0" class="hero__progress">
            <div class="hero__progress-head tabular">
              <span>已看 {{ formatDuration(item.progressSeconds) }}</span>
              <span>上次观看 {{ formatDate(item.lastPlayedAt) }}</span>
            </div>
            <div class="hero__progress-bar">
              <span
                class="hero__progress-fill"
                :style="{ width: `${progressRatio(item.progressSeconds, item.durationSeconds) * 100}%` }"
              />
            </div>
          </div>

          <div class="hero__actions">
            <AppButton
              variant="primary"
              :disabled="!canPlay"
              :title="canPlay ? '' : '播放适配器未就绪'"
              @click="router.push({ name: 'player', params: { id: item.id } })"
            >
              <AppIcon name="play" :size="16" />
              {{ item.progressSeconds > 0 ? '继续播放' : '播放' }}
            </AppButton>
            <AppButton :loading="favoriteBusy" @click="toggleFavorite">
              <AppIcon :name="item.favorite ? 'heart-filled' : 'heart'" :size="16" />
              {{ item.favorite ? '已收藏' : '收藏' }}
            </AppButton>
          </div>
          <p v-if="!canPlay" class="hero__hint">播放服务未就绪，接入 115 播放适配器后可用</p>
          <p v-if="favoriteError" class="hero__error">{{ favoriteError }}</p>
        </div>
      </section>

      <section class="panels">
        <div class="panel">
          <h2 class="panel__title">音轨</h2>
          <p v-if="!item.audioTracks.length" class="panel__empty">没有可切换的音轨</p>
          <ul v-else class="panel__list">
            <li v-for="track in item.audioTracks" :key="track.id" class="panel__row">
              <span class="panel__name">{{ track.label }}</span>
              <AppBadge>{{ track.lang }}</AppBadge>
              <span v-if="track.codec" class="panel__sub">{{ track.codec }}</span>
            </li>
          </ul>
        </div>

        <div class="panel">
          <h2 class="panel__title">字幕</h2>
          <p v-if="!item.subtitles.length" class="panel__empty">没有字幕</p>
          <ul v-else class="panel__list">
            <li v-for="track in item.subtitles" :key="track.id" class="panel__row">
              <span class="panel__name">{{ track.label }}</span>
              <AppBadge>{{ track.lang }}</AppBadge>
              <span class="panel__sub">{{ track.embedded ? '内嵌' : track.format.toUpperCase() }}</span>
            </li>
          </ul>
        </div>

        <div class="panel">
          <h2 class="panel__title">来源</h2>
          <dl class="panel__kv">
            <dt>资源源</dt>
            <dd>{{ item.sourceProvider ?? '—' }}</dd>
            <dt>远端路径</dt>
            <dd class="panel__path">{{ item.remotePath ?? '—' }}</dd>
          </dl>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.detail {
  display: flex;
  flex-direction: column;
  gap: var(--space5);
  /* 宽度与内边距由 AppShell 统一处理 */
  padding: 0;
}

.detail__back {
  display: inline-flex;
  align-items: center;
  gap: var(--space1);
  align-self: flex-start;
  height: 32px;
  padding: 0 var(--space2);
  border-radius: var(--radius-sm);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.detail__back:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
}

/* 主信息区：海报与文字同在一张主卡上，减少大片飘散的留白 */
.hero {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--space6);
  align-items: start;
  padding: var(--space6);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.hero__body {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  min-width: 0;
}

.hero__title {
  font-size: var(--font-heading1-size);
  font-weight: var(--font-heading1-weight);
  letter-spacing: var(--font-heading1-tracking);
}

.hero__original {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.hero__meta {
  display: flex;
  gap: var(--space2);
  flex-wrap: wrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.hero__overview {
  font-size: var(--font-caption-size);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.hero__progress {
  display: flex;
  flex-direction: column;
  gap: var(--space1);
  padding: var(--space3);
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
}

.hero__progress-head {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.hero__progress-bar {
  height: 4px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  overflow: hidden;
}

.hero__progress-fill {
  display: block;
  height: 100%;
  background: var(--color-primary);
}

.hero__actions {
  display: flex;
  gap: var(--space2);
  flex-wrap: wrap;
  margin-top: var(--space2);
}

.hero__hint,
.hero__error {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.hero__error {
  color: var(--color-danger);
}

.panels {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space4);
}

.panel {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  padding: var(--space5);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.panel__title {
  font-size: var(--font-label-size);
  font-weight: 600;
}

.panel__empty {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.panel__list {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.panel__row {
  display: flex;
  align-items: center;
  gap: var(--space2);
  font-size: var(--font-caption-size);
}

.panel__name {
  flex: 1;
}

.panel__sub {
  color: var(--color-text-secondary);
}

.panel__kv {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space2);
  margin: 0;
  font-size: var(--font-caption-size);
}

.panel__kv dt {
  color: var(--color-text-secondary);
}

.panel__kv dd {
  margin: 0;
  color: var(--color-text-secondary);
  min-width: 0;
}

.panel__path {
  overflow-wrap: anywhere;
}

.detail__skeleton {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--space6);
}

.detail__skeleton-body {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

@media (max-width: 640px) {
  .hero,
  .detail__skeleton {
    grid-template-columns: 1fr;
  }
  .hero {
    gap: var(--space4);
    padding: var(--space4);
    border-radius: var(--radius-xl);
  }
  .hero > :first-child {
    max-width: 200px;
  }
}
</style>
