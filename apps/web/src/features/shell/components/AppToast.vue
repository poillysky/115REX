<script setup lang="ts">
// 轻提示（docs/02 §10 AppToast）：右下角堆叠，不阻断操作，不与 Dialog 混用。
// 进入 / 退出都是短促的位移 + 淡入淡出；悬停暂停倒计时不做假动画，只保留一键关闭。
import AppIcon from '@/features/shell/components/AppIcon.vue'
import type { IconName } from '@/features/shell/components/icon-names'
import { useNotifyStore, type NoticeTone } from '@/application/notify'

const notify = useNotifyStore()

const ICONS: Record<NoticeTone, IconName> = {
  info: 'bell',
  success: 'check',
  warning: 'alert',
  danger: 'alert',
}

const LABELS: Record<NoticeTone, string> = {
  info: '提示',
  success: '完成',
  warning: '注意',
  danger: '失败',
}

function runAction(id: number, run: () => void): void {
  notify.dismiss(id)
  run()
}
</script>

<template>
  <Teleport to="body">
    <div class="toasts" role="region" aria-label="操作反馈">
      <TransitionGroup name="toast" tag="div" class="toasts__stack">
        <div
          v-for="item in notify.items"
          :key="item.id"
          class="toast"
          :class="`toast--${item.tone}`"
        >
          <span class="toast__icon" aria-hidden="true">
            <AppIcon :name="ICONS[item.tone]" :size="18" />
          </span>

          <div class="toast__main">
            <span class="visually-hidden">{{ LABELS[item.tone] }}：</span>
            <p class="toast__text">{{ item.message }}</p>
          </div>

          <button
            v-if="item.action"
            type="button"
            class="toast__action"
            @click="runAction(item.id, item.action.run)"
          >
            {{ item.action.label }}
          </button>

          <button
            type="button"
            class="toast__close"
            aria-label="关闭提示"
            @click="notify.dismiss(item.id)"
          >
            <AppIcon name="close" :size="15" />
          </button>
        </div>
      </TransitionGroup>

      <!-- 读屏播报：视觉上不可见，避免重复朗读可见文本 -->
      <p class="visually-hidden" aria-live="polite" aria-atomic="true">
        {{ notify.items.at(-1)?.message ?? '' }}
      </p>
    </div>
  </Teleport>
</template>

<style scoped>
.toasts {
  position: fixed;
  right: var(--space5);
  bottom: var(--space5);
  z-index: 90;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  pointer-events: none;
}

.toasts__stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space2);
}

/* Level 3 浮层：轻磨砂 + 品牌投影，不压成模态（docs/02 §6） */
.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space3);
  width: 340px;
  max-width: calc(100vw - var(--space6));
  padding: var(--space3) var(--space3) var(--space3) var(--space4);
  border-radius: var(--radius-lg);
  border: 1px solid color-mix(in srgb, var(--highlight-line) 55%, var(--color-border-soft));
  background: color-mix(in srgb, var(--color-surface) 86%, transparent);
  backdrop-filter: blur(18px) saturate(1.25);
  -webkit-backdrop-filter: blur(18px) saturate(1.25);
  box-shadow:
    inset 0 1px 0 var(--highlight-line),
    var(--shadow-overlay);
  pointer-events: auto;
}

.toast__icon {
  display: grid;
  place-items: center;
  flex: none;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.toast--success .toast__icon {
  color: var(--color-success);
}
.toast--warning .toast__icon {
  color: var(--color-warning);
}
.toast--danger .toast__icon {
  color: var(--color-danger);
}

.toast__main {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.toast__text {
  max-width: none;
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-primary);
}

.toast__action {
  flex: none;
  align-self: center;
  height: 26px;
  padding: 0 var(--space2);
  border-radius: var(--radius-sm);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
  transition: background-color var(--duration-micro) ease;
}

.toast__action:hover {
  background: var(--color-separator);
}

.toast__close {
  display: grid;
  place-items: center;
  flex: none;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition:
    color var(--duration-micro) ease,
    background-color var(--duration-micro) ease;
}

.toast__close:hover {
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
}

/* 进入：从右侧轻微推入；退出：淡出并收高，避免列表跳动 */
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity var(--duration-page) ease,
    transform var(--duration-page) cubic-bezier(0.2, 0.8, 0.2, 1);
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(12px);
}

.toast-leave-active {
  position: absolute;
}

.toast-move {
  transition: transform var(--duration-page) ease;
}

@media (max-width: 640px) {
  .toasts {
    right: var(--space3);
    left: var(--space3);
    bottom: var(--space3);
    align-items: stretch;
  }

  .toasts__stack {
    align-items: stretch;
  }

  .toast {
    width: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-from,
  .toast-leave-to {
    transform: none;
  }
}
</style>
