<script setup lang="ts">
// 骨架块（docs/03 §6：加载优先骨架屏，尺寸与真实内容一致）。
// 只负责灰度形状，尺寸由调用方给。

withDefaults(defineProps<{ height?: string; radius?: string; width?: string }>(), {
  height: '16px',
  radius: 'var(--radius-sm)',
  width: '100%',
})
</script>

<template>
  <span class="skeleton" :style="{ height, width, borderRadius: radius }" aria-hidden="true" />
</template>

<style scoped>
/* 呼吸节奏挂在 --duration-page 上：节奏感来自同一套动效 Token，不写裸毫秒 */
.skeleton {
  display: block;
  background: var(--color-surface-secondary);
  animation: skeleton-pulse calc(var(--duration-page) * 5) ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.55;
  }
}
</style>
