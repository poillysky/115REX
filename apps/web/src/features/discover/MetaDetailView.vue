<script setup lang="ts">
// 元数据详情：海报 / 简介 / 演职员；不做播放（影视库条目另走 /library/:id）。
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { metaApi } from '@/data/api'
import { describeError } from '@/core/api/error'
import type { MetaDetail, MetaKind, MetaSource } from '@/domain/contract'
import AppArtwork from '@/features/shell/components/AppArtwork.vue'
import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const errorText = ref('')
const detail = ref<MetaDetail | null>(null)

const source = computed(() => String(route.params.source || '') as MetaSource)
const id = computed(() => String(route.params.id || ''))
const kind = computed(() => {
  const q = String(route.query.kind || 'movie')
  return (q === 'tv' ? 'tv' : 'movie') as MetaKind
})

async function load(): Promise<void> {
  if (!source.value || !id.value) {
    detail.value = null
    errorText.value = '缺少条目参数'
    return
  }
  loading.value = true
  errorText.value = ''
  try {
    detail.value = await metaApi.detail(source.value, id.value, kind.value)
  } catch (error) {
    errorText.value = describeError(error)
    detail.value = null
  } finally {
    loading.value = false
  }
}

function goBack(): void {
  if (window.history.length > 1) router.back()
  else void router.push({ name: 'discover-movie' })
}

watch(
  () => [source.value, id.value, kind.value] as const,
  () => void load(),
  { immediate: true },
)
</script>

<template>
  <div class="meta">
    <button type="button" class="meta__back" @click="goBack">
      <AppIcon name="chevron-left" :size="18" />
      返回
    </button>

    <AppErrorState v-if="errorText && !detail" :message="errorText" @retry="load" />

    <div v-else-if="loading && !detail" class="meta__skel">
      <AppSkeleton height="0" style="aspect-ratio: 2 / 3; height: auto" radius="var(--radius-xl)" />
      <div class="meta__skel-body">
        <AppSkeleton height="30px" width="60%" />
        <AppSkeleton height="16px" width="40%" />
        <AppSkeleton height="88px" radius="var(--radius-lg)" />
      </div>
    </div>

    <AppEmptyState
      v-else-if="!detail"
      title="条目不存在"
      description="可能已被下架，回到影视海报墙再选"
      icon="film"
    >
      <AppButton size="sm" @click="router.push({ name: 'discover-movie' })">回到影视</AppButton>
    </AppEmptyState>

    <template v-else>
      <section class="hero">
        <AppArtwork :src="detail.posterUrl" :alt="detail.title" radius="var(--radius-xl)" />
        <div class="hero__body">
          <div class="hero__badges">
            <AppBadge tone="primary">{{ detail.source === 'douban' ? '豆瓣' : 'TMDB' }}</AppBadge>
            <AppBadge>{{ detail.kind === 'tv' ? '剧集' : '电影' }}</AppBadge>
          </div>
          <h1 class="hero__title">{{ detail.title }}</h1>
          <p v-if="detail.originalTitle" class="hero__original">{{ detail.originalTitle }}</p>
          <div class="hero__meta tabular">
            <span>{{ detail.year ?? '年份未知' }}</span>
            <span v-if="detail.runtimeMinutes != null">·</span>
            <span v-if="detail.runtimeMinutes != null">{{ detail.runtimeMinutes }} 分钟</span>
            <span v-if="detail.rating != null">·</span>
            <span v-if="detail.rating != null">{{ detail.rating.toFixed(1) }} 分</span>
          </div>
          <div v-if="detail.genres.length" class="hero__genres">
            <AppBadge v-for="genre in detail.genres" :key="genre">{{ genre }}</AppBadge>
          </div>
          <p v-if="detail.overview" class="hero__overview">{{ detail.overview }}</p>
          <div v-if="detail.homepage" class="hero__actions">
            <a
              class="hero__link"
              :href="detail.homepage"
              target="_blank"
              rel="noopener noreferrer"
            >
              <AppIcon name="link" :size="14" />
              打开主页
            </a>
          </div>
        </div>
      </section>

      <section v-if="detail.cast.length" class="cast">
        <h2 class="cast__title">演职员</h2>
        <ul class="cast__list">
          <li v-for="person in detail.cast" :key="`${person.id}-${person.name}`" class="cast__item">
            <AppArtwork
              :src="person.profileUrl"
              :alt="person.name"
              ratio="1 / 1"
              radius="var(--radius-full)"
            />
            <div class="cast__text">
              <span class="cast__name">{{ person.name }}</span>
              <span v-if="person.character" class="cast__role">{{ person.character }}</span>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.meta {
  display: flex;
  flex-direction: column;
  gap: var(--space5);
}

.meta__back {
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

.meta__back:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
}

.meta__skel {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: var(--space6);
}

.meta__skel-body {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

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

.hero__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space2);
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
  flex-wrap: wrap;
  gap: var(--space2);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.hero__genres {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space2);
}

.hero__overview {
  font-size: var(--font-caption-size);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.hero__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space2);
}

.hero__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space1);
  height: 32px;
  padding: 0 var(--space3);
  border-radius: var(--radius-md);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  background: var(--color-surface-secondary);
}

.hero__link:hover {
  color: var(--color-text-primary);
}

.cast {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
  padding: var(--space5);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
}

.cast__title {
  font-size: var(--font-heading2-size, 1.05rem);
  font-weight: 600;
}

.cast__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: var(--space4);
  list-style: none;
  margin: 0;
  padding: 0;
}

.cast__item {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: var(--space3);
  align-items: center;
}

.cast__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.cast__name {
  font-size: var(--font-caption-size);
  font-weight: 600;
}

.cast__role {
  font-size: 12px;
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .hero,
  .meta__skel {
    grid-template-columns: 140px 1fr;
    gap: var(--space4);
    padding: var(--space4);
  }
}
</style>
