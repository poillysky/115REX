<script setup lang="ts">
// 横滑榜单轨：对齐 MoviePilot VirtualSlideView——隐藏滚动条、悬停左右键、鼠标拖动滚动。
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from '@/features/shell/components/AppIcon.vue'

const railRef = ref<HTMLElement | null>(null)
const canPrev = ref(false)
const canNext = ref(false)
const isScrolling = ref(false)
const isDragging = ref(false)

let scrollTimer: number | null = null
let dragPointerId: number | null = null
let dragStartX = 0
let dragStartScroll = 0
let dragMoved = false
const DRAG_THRESHOLD = 4

function updateNav(): void {
  const el = railRef.value
  if (!el) {
    canPrev.value = false
    canNext.value = false
    return
  }
  const max = el.scrollWidth - el.clientWidth
  canPrev.value = el.scrollLeft > 2
  canNext.value = el.scrollLeft < max - 2
}

function markScrolling(): void {
  isScrolling.value = true
  if (scrollTimer != null) window.clearTimeout(scrollTimer)
  scrollTimer = window.setTimeout(() => {
    isScrolling.value = false
    scrollTimer = null
  }, 1200)
}

function onScroll(): void {
  updateNav()
  markScrolling()
}

function slide(next: boolean): void {
  const el = railRef.value
  if (!el) return
  const step = Math.max(el.clientWidth * 0.85, 280)
  const target = next
    ? Math.min(el.scrollLeft + step, el.scrollWidth - el.clientWidth)
    : Math.max(el.scrollLeft - step, 0)
  el.scrollTo({ left: target, behavior: 'smooth' })
  markScrolling()
}

function onPointerDown(event: PointerEvent): void {
  if (event.button !== 0 || event.pointerType === 'touch') return
  const el = railRef.value
  if (!el) return
  dragPointerId = event.pointerId
  dragStartX = event.clientX
  dragStartScroll = el.scrollLeft
  dragMoved = false
  isDragging.value = true
  el.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent): void {
  if (dragPointerId !== event.pointerId || !isDragging.value) return
  const el = railRef.value
  if (!el) return
  const delta = event.clientX - dragStartX
  if (Math.abs(delta) > DRAG_THRESHOLD) dragMoved = true
  el.scrollLeft = dragStartScroll - delta
  updateNav()
}

function endDrag(event: PointerEvent): void {
  if (dragPointerId !== event.pointerId) return
  const el = railRef.value
  if (el?.hasPointerCapture(event.pointerId)) {
    el.releasePointerCapture(event.pointerId)
  }
  isDragging.value = false
  dragPointerId = null
  if (dragMoved) {
    // 吞掉随后的 click，避免拖动松手误进详情
    const swallow = (e: Event) => {
      e.stopPropagation()
      e.preventDefault()
      el?.removeEventListener('click', swallow, true)
    }
    el?.addEventListener('click', swallow, true)
    window.setTimeout(() => el?.removeEventListener('click', swallow, true), 0)
  }
  dragMoved = false
  markScrolling()
}

let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  await nextTick()
  updateNav()
  const el = railRef.value
  if (!el || typeof ResizeObserver === 'undefined') return
  resizeObserver = new ResizeObserver(() => updateNav())
  resizeObserver.observe(el)
})

onBeforeUnmount(() => {
  if (scrollTimer != null) window.clearTimeout(scrollTimer)
  resizeObserver?.disconnect()
  resizeObserver = null
})

defineExpose({ updateNav })
</script>

<template>
  <div class="rail-wrap" :class="{ 'is-scrolling': isScrolling, 'is-dragging': isDragging }">
    <div
      ref="railRef"
      class="rail"
      @scroll.passive="onScroll"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="endDrag"
      @pointercancel="endDrag"
    >
      <slot />
    </div>

    <button
      v-show="canPrev"
      type="button"
      class="rail__nav rail__nav--prev"
      aria-label="向左滚动"
      @click.stop="slide(false)"
    >
      <AppIcon name="chevron-left" :size="22" />
    </button>
    <button
      v-show="canNext"
      type="button"
      class="rail__nav rail__nav--next"
      aria-label="向右滚动"
      @click.stop="slide(true)"
    >
      <AppIcon name="chevron-right" :size="22" />
    </button>
  </div>
</template>

<style scoped>
.rail-wrap {
  position: relative;
  isolation: isolate;
}

.rail {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 8px 4px 14px;
  scroll-behavior: auto;
  overscroll-behavior-x: contain;
  cursor: grab;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.rail::-webkit-scrollbar {
  display: none;
}

.rail-wrap.is-dragging .rail {
  cursor: grabbing;
  scroll-behavior: auto;
  user-select: none;
}

.rail__nav {
  position: absolute;
  top: 50%;
  z-index: 5;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  margin: 0;
  padding: 0;
  border: 1px solid rgb(255 255 255 / 14%);
  border-radius: 999px;
  color: #fff;
  background: rgb(8 18 28 / 52%);
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 22px rgb(0 0 0 / 22%);
  transform: translateY(-58%);
  opacity: 0;
  pointer-events: none;
  transition:
    opacity 0.25s ease,
    transform 0.25s cubic-bezier(0.25, 0.8, 0.25, 1),
    background-color 0.25s ease;
}

.rail__nav--prev {
  left: 6px;
}

.rail__nav--next {
  right: 6px;
}

.rail__nav:hover {
  background: rgb(8 18 28 / 72%);
  transform: translateY(-58%) scale(1.05);
}

@media (hover: hover) {
  .rail-wrap:hover .rail__nav,
  .rail-wrap.is-scrolling .rail__nav {
    opacity: 1;
    pointer-events: auto;
  }
}

@media (hover: none) {
  .rail {
    cursor: default;
  }

  .rail__nav {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .rail__nav {
    transition: none;
  }
}
</style>
