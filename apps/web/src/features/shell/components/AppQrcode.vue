<script setup lang="ts">
// 二维码图形。传入的是二维码**内容**（如 115 扫码链接），这里负责渲染成像素图。
import { computed } from 'vue'

import { encodeQr } from '@/core/qr'

const props = withDefaults(defineProps<{ value: string; size?: number; label?: string }>(), {
  size: 176,
  label: '扫码二维码',
})

const modules = computed<boolean[][]>(() => {
  if (!props.value) return []
  try {
    return encodeQr(props.value)
  } catch {
    return []
  }
})

const dim = computed(() => modules.value.length)

// 4 个模块的静区让扫描器能锁定边界
const path = computed(() => {
  const parts: string[] = []
  modules.value.forEach((row, r) => {
    row.forEach((dark, c) => {
      if (dark) parts.push(`M${c + 4} ${r + 4}h1v1h-1z`)
    })
  })
  return parts.join('')
})

const viewBox = computed(() => `0 0 ${dim.value + 8} ${dim.value + 8}`)
</script>

<template>
  <svg
    v-if="dim"
    class="qr"
    :width="size"
    :height="size"
    :viewBox="viewBox"
    role="img"
    :aria-label="label"
    shape-rendering="crispEdges"
  >
    <rect :width="dim + 8" :height="dim + 8" fill="#fff" />
    <path :d="path" fill="#000" />
  </svg>
</template>

<style scoped>
.qr {
  display: block;
  border-radius: var(--radius-md);
  background: #fff;
}
</style>
