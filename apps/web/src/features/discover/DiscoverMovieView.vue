<script setup lang="ts">
// 影视推荐首页：对齐 MoviePilot recommend——顶部分类 Tab + 分栏横滑榜单
// （流行趋势 / 正在热映 / 热门电影 …）。
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { metaApi } from '@/data/api'
import { ApiError, describeError } from '@/core/api/error'
import type { MetaBoard, MetaCard, MetaKind, MetaSource } from '@/domain/contract'
import BoardRail from '@/features/discover/BoardRail.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'

const router = useRouter()

type TabKey = 'all' | 'movie' | 'tv' | 'anime' | 'ranking'

const TABS: { id: TabKey; label: string }[] = [
  { id: 'all', label: '全部' },
  { id: 'movie', label: '电影' },
  { id: 'tv', label: '电视剧' },
  { id: 'anime', label: '动漫' },
  { id: 'ranking', label: '榜单' },
]

const tab = ref<TabKey>('all')
const boards = ref<MetaBoard[]>([])
const loading = ref(true)
const errorText = ref('')
const needsSetup = ref(false)

const visibleBoards = computed(() => {
  if (tab.value === 'all') return boards.value.filter((b) => b.items.length)
  return boards.value.filter((b) => b.group === tab.value && b.items.length)
})

function kindLabel(card: MetaCard): string {
  return card.kind === 'tv' ? '电视剧' : '电影'
}

function ratingText(value: number | null): string {
  if (value == null || Number.isNaN(value)) return ''
  return value.toFixed(1)
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  needsSetup.value = false
  try {
    const response = await metaApi.boards()
    boards.value = response.boards
    if (!response.boards.some((b) => b.items.length)) {
      const msg = response.boards.map((b) => b.message).find(Boolean) || '暂无推荐内容'
      errorText.value = msg
      needsSetup.value = msg.includes('API Key') || msg.includes('插件')
    }
  } catch (error) {
    errorText.value = describeError(error)
    const code =
      error instanceof ApiError
        ? error.code
        : error && typeof error === 'object' && 'code' in error
          ? String((error as { code: unknown }).code)
          : ''
    needsSetup.value = code === 'PROVIDER_NOT_READY'
    boards.value = []
  } finally {
    loading.value = false
  }
}

function openDetail(card: MetaCard): void {
  void router.push({
    name: 'meta-detail',
    params: { source: card.source as MetaSource, id: card.id },
    query: { kind: card.kind as MetaKind },
  })
}

function hideBrokenPoster(event: Event): void {
  const img = event.target
  if (img instanceof HTMLImageElement) img.style.opacity = '0'
}

void load()
</script>

<template>
  <div class="discover">
    <nav class="discover__tabs" role="tablist" aria-label="内容分类">
      <button
        v-for="item in TABS"
        :key="item.id"
        type="button"
        class="tab"
        :class="{ 'is-active': tab === item.id }"
        role="tab"
        :aria-selected="tab === item.id"
        @click="tab = item.id"
      >
        {{ item.label }}
      </button>
    </nav>

    <AppEmptyState
      v-if="needsSetup && errorText && !visibleBoards.length && !loading"
      title="还差一步配置"
      :description="errorText"
      icon="puzzle"
    >
      <AppButton size="sm" variant="primary" @click="router.push({ name: 'system-plugins' })">
        打开插件管理
      </AppButton>
      <AppButton size="sm" @click="load">重试</AppButton>
    </AppEmptyState>

    <AppErrorState
      v-else-if="errorText && !visibleBoards.length && !loading"
      :message="errorText"
      @retry="load"
    />

    <div v-else-if="loading" class="boards" aria-busy="true">
      <section v-for="n in 3" :key="n" class="board">
        <div class="board__head">
          <AppSkeleton height="22px" width="120px" />
        </div>
        <BoardRail>
          <AppSkeleton
            v-for="m in 8"
            :key="m"
            height="0"
            style="width: 132px; aspect-ratio: 2 / 3; height: auto; flex: 0 0 auto"
            radius="var(--radius-md)"
          />
        </BoardRail>
      </section>
    </div>

    <AppEmptyState
      v-else-if="!visibleBoards.length"
      title="这一类还没有内容"
      description="换个分类看看，或稍后再刷新"
      icon="film"
    >
      <AppButton size="sm" @click="tab = 'all'">查看全部</AppButton>
    </AppEmptyState>

    <div v-else class="boards">
      <section v-for="board in visibleBoards" :key="board.id" class="board">
        <header class="board__head">
          <h2 class="board__title">{{ board.title }}</h2>
        </header>

        <BoardRail>
          <button
            v-for="(card, index) in board.items"
            :key="`${board.id}-${card.source}-${card.id}`"
            type="button"
            class="poster"
            :aria-label="card.title"
            @click="openDetail(card)"
          >
            <span class="poster__frame">
              <img
                v-if="card.posterUrl"
                class="poster__img"
                :src="card.posterUrl"
                :alt="card.title"
                :loading="index < 8 ? 'eager' : 'lazy'"
                decoding="async"
                :fetchpriority="index < 4 ? 'high' : 'auto'"
                referrerpolicy="no-referrer"
                @error="hideBrokenPoster"
              />
              <span v-else class="poster__fallback" aria-hidden="true">{{ card.title.slice(0, 1) }}</span>

              <span class="poster__chip poster__chip--kind">{{ kindLabel(card) }}</span>
              <span v-if="ratingText(card.rating)" class="poster__chip poster__chip--rating tabular">
                {{ ratingText(card.rating) }}
              </span>

              <span class="poster__veil">
                <span class="poster__name">{{ card.title }}</span>
              </span>
            </span>
          </button>
        </BoardRail>
      </section>
    </div>
  </div>
</template>

<style scoped>
.discover {
  display: flex;
  flex-direction: column;
  gap: var(--space5);
}

.discover__tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 18px;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--panel-border);
}

.tab {
  position: relative;
  height: 40px;
  padding: 0 2px;
  border: 0;
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--font-caption-size);
  font-weight: 600;
  cursor: pointer;
}

.tab:hover {
  color: var(--color-text-primary);
}

.tab.is-active {
  color: var(--color-primary);
}

.tab.is-active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: var(--color-primary);
}

.tab:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
  border-radius: 4px;
}

.boards {
  display: flex;
  flex-direction: column;
  gap: var(--space6);
}

.board__head {
  display: flex;
  align-items: center;
  margin-bottom: var(--space3);
}

.board__title {
  margin: 0;
  padding-left: 12px;
  border-left: 4px solid var(--color-primary);
  font-size: var(--font-heading2-size, 1.15rem);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.poster {
  flex: 0 0 auto;
  width: 132px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  color: inherit;
  text-align: left;
}

.poster:focus-visible .poster__frame {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

.poster__frame {
  position: relative;
  display: block;
  width: 132px;
  aspect-ratio: 2 / 3;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--color-surface-secondary);
  box-shadow: var(--shadow-card);
  transition:
    transform 220ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 220ms ease;
}

.poster:hover .poster__frame,
.poster:focus-visible .poster__frame {
  transform: translateY(-4px) scale(1.03);
  box-shadow:
    0 12px 28px rgb(0 0 0 / 18%),
    0 2px 6px rgb(0 0 0 / 8%);
}

.poster__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.poster__fallback {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
  font-size: 26px;
  font-weight: 700;
  color: var(--color-text-tertiary, var(--color-text-secondary));
}

.poster__chip {
  position: absolute;
  top: 8px;
  z-index: 2;
  height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  line-height: 22px;
  color: #fff;
  box-shadow: 0 1px 3px rgb(0 0 0 / 22%);
}

.poster__chip--kind {
  left: 8px;
  background: color-mix(in srgb, var(--color-primary) 86%, #000);
}

.poster__chip--rating {
  right: 8px;
  background: color-mix(in srgb, var(--color-primary) 70%, #5b21b6);
}

.poster__veil {
  position: absolute;
  inset: auto 0 0;
  z-index: 1;
  padding: 28px 8px 8px;
  color: #fff;
  background: linear-gradient(180deg, transparent, rgb(16 18 24 / 86%));
  opacity: 0;
  transform: translateY(4px);
  transition:
    opacity 180ms ease,
    transform 200ms cubic-bezier(0.22, 1, 0.36, 1);
  pointer-events: none;
}

.poster:hover .poster__veil,
.poster:focus-visible .poster__veil {
  opacity: 1;
  transform: translateY(0);
}

.poster__name {
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (hover: none) {
  .poster__veil {
    opacity: 1;
    transform: none;
  }

  .poster:hover .poster__frame,
  .poster:focus-visible .poster__frame {
    transform: none;
  }
}

@media (max-width: 720px) {
  .poster,
  .poster__frame {
    width: 112px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .poster__frame,
  .poster__veil {
    transition: none;
  }

  .poster:hover .poster__frame,
  .poster:focus-visible .poster__frame {
    transform: none;
  }
}
</style>
