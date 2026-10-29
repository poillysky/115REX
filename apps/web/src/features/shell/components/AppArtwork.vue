<script setup lang="ts">
// 海报（docs/02 §7.4 AppMediaArtwork）：加载中 / 失败 / 缺失三种状态统一占位，不叠品牌色。
import { ref, watch } from 'vue'

import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'

const props = withDefaults(
  defineProps<{
    src: string | null
    alt: string
    ratio?: string
    radius?: string
  }>(),
  { ratio: '2 / 3', radius: 'var(--radius-lg)' },
)

const state = ref<'loading' | 'ready' | 'failed'>(props.src ? 'loading' : 'failed')

watch(
  () => props.src,
  (value) => {
    state.value = value ? 'loading' : 'failed'
  },
)
</script>

<template>
  <div class="artwork" :style="{ aspectRatio: ratio, borderRadius: radius }">
    <AppSkeleton v-if="state === 'loading'" height="0" :radius="radius" style="height: auto; aspect-ratio: inherit" />
    <img
      v-if="props.src && state !== 'failed'"
      class="artwork__img"
      :src="props.src"
      :alt="props.alt"
      loading="lazy"
      decoding="async"
      @load="state = 'ready'"
      @error="state = 'failed'"
    />
    <div v-if="state === 'failed'" class="artwork__fallback" role="img" :aria-label="props.alt">
      <span>{{ props.alt.slice(0, 1) }}</span>
    </div>
  </div>
</template>

<style scoped>
.artwork {
  position: relative;
  overflow: hidden;
  background: var(--color-surface-secondary);
}

.artwork__img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.artwork__fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  font-size: var(--font-heading2-size);
  font-weight: var(--font-heading2-weight);
  color: var(--color-text-secondary);
  background: var(--color-surface-secondary);
}
</style>
