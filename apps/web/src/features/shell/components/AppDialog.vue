<script setup lang="ts">
// 通用对话框（docs/02 §10 AppDialog / §9.3 模态任务）。
// 负责遮罩、焦点进出、Esc 关闭与背景滚动锁定；内容与动作由调用方用插槽给出。
// tone 只表达「这是什么性质的决定」：破坏性操作标红图标，不铺大色块。
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

import AppIcon from '@/features/shell/components/AppIcon.vue'
import type { IconName } from '@/features/shell/components/icon-names'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    description?: string
    size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl'
    /** neutral 普通信息；danger 破坏性确认；success 结果告知 */
    tone?: 'neutral' | 'danger' | 'success'
    /** center 居中；top 靠上并向下弹入 */
    placement?: 'center' | 'top'
    closeOnOverlay?: boolean
  }>(),
  { description: '', size: 'md', tone: 'neutral', placement: 'center', closeOnOverlay: true },
)

const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const TONE_ICON: Record<'neutral' | 'danger' | 'success', IconName | null> = {
  neutral: null,
  danger: 'alert',
  success: 'check',
}

const uid = useId()
const titleId = `${uid}-title`
const descriptionId = `${uid}-desc`

const card = ref<HTMLElement | null>(null)
const icon = ref(TONE_ICON[props.tone])
let lastFocused: HTMLElement | null = null
let previousOverflow = ''

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'

function close(): void {
  emit('update:open', false)
}

/** Tab 只在对话框内循环，避免焦点跑到背后的页面。Esc 在捕获阶段处理，内层编辑器先拦到自己身上。 */
function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    close()
    return
  }
  if (event.key !== 'Tab') return

  const root = card.value
  if (!root) return
  const items = Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (item) => item.offsetParent !== null,
  )
  if (!items.length) {
    event.preventDefault()
    root.focus()
    return
  }

  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && (document.activeElement === first || document.activeElement === root)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      icon.value = TONE_ICON[props.tone]
      lastFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      // 捕获阶段抢在页面快捷键之前，避免 Esc 只被某一层消费
      window.addEventListener('keydown', onKeydown, true)
      await nextTick()
      const target = card.value?.querySelector<HTMLElement>(FOCUSABLE) ?? card.value
      target?.focus()
      return
    }

    window.removeEventListener('keydown', onKeydown, true)
    document.body.style.overflow = previousOverflow
    if (lastFocused?.isConnected) lastFocused.focus()
    lastFocused = null
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown, true)
  document.body.style.overflow = previousOverflow
})
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div
        v-if="open"
        class="dialog"
        :class="[`dialog--${placement}`]"
        @click.self="closeOnOverlay && close()"
      >
        <div
          ref="card"
          class="dialog__card"
          :class="[`dialog__card--${size}`, `dialog__card--${tone}`, `dialog__card--${placement}`]"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="description ? descriptionId : undefined"
          tabindex="-1"
        >
          <header class="dialog__head">
            <span v-if="icon" class="dialog__badge" aria-hidden="true">
              <AppIcon :name="icon" :size="18" />
            </span>
            <div class="dialog__head-main">
              <h2 :id="titleId" class="dialog__title">{{ title }}</h2>
              <p v-if="description" :id="descriptionId" class="dialog__desc">{{ description }}</p>
            </div>
            <button type="button" class="dialog__close" aria-label="关闭" @click="close">
              <AppIcon name="close" :size="18" />
            </button>
          </header>

          <div v-if="$slots.default" class="dialog__body">
            <slot />
          </div>

          <footer v-if="$slots.footer" class="dialog__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dialog {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space4);
  background: color-mix(in srgb, #000 40%, transparent); /* taste-skill-ignore：模态遮罩，非装饰色 */
  backdrop-filter: blur(8px) saturate(1.1);
  -webkit-backdrop-filter: blur(8px) saturate(1.1);
}

.dialog--top {
  align-items: flex-start;
  padding-top: clamp(48px, 8vh, 96px);
}

.dialog__card {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-height: calc(100vh - var(--space8));
  border-radius: var(--radius-xl);
  border: 1px solid var(--panel-border);
  background: var(--chrome-float);
  backdrop-filter: var(--chrome-blur);
  -webkit-backdrop-filter: var(--chrome-blur);
  /* 模态是唯一允许「浮起来」的层：柔和低对比，不产生黑边 */
  box-shadow:
    inset 0 1px 0 var(--highlight-line),
    var(--shadow-overlay);
  overflow: hidden;
  outline: none;
}

.dialog__card--sm {
  max-width: 440px;
}

.dialog__card--md {
  max-width: 620px;
}

.dialog__card--lg {
  max-width: 720px;
}

/* 表单类弹窗：加宽后能用两栏铺开字段，避免竖向拉得过长 */
.dialog__card--xl {
  max-width: 940px;
}

/* 探测结果这类宽列表弹窗：一行放得下标题和五列统计，不靠截断省地方 */
.dialog__card--2xl {
  max-width: min(1880px, calc(100vw - var(--space8)));
}

.dialog__head {
  display: flex;
  align-items: flex-start;
  gap: var(--space3);
  padding: var(--space5) var(--space6) var(--space4);
}

/* 有正文或页脚时才需要分隔线，纯信息弹窗保持通透 */
.dialog__head:has(+ .dialog__body),
.dialog__head:has(+ .dialog__footer) {
  border-bottom: 1px solid var(--panel-divider);
  padding-bottom: var(--space4);
}

.dialog__badge {
  display: grid;
  place-items: center;
  flex: none;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.dialog__card--danger .dialog__badge {
  color: var(--color-danger);
}

.dialog__card--success .dialog__badge {
  color: var(--color-success);
}

.dialog__head-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: var(--space1);
  min-width: 0;
  justify-content: center;
  min-height: 32px;
}

.dialog__title {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  letter-spacing: var(--font-heading3-tracking);
  line-height: 1.3;
  color: var(--color-text-primary);
}

.dialog__desc {
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.dialog__close {
  display: grid;
  flex: none;
  place-items: center;
  width: 28px;
  height: 28px;
  margin-left: auto;
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.dialog__close:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.dialog__body {
  padding: var(--space5) var(--space6);
  overflow-y: auto;
}

.dialog__footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space2);
  padding: var(--space3) var(--space6) var(--space5);
  border-top: 1px solid var(--panel-divider);
}

/* 进入 / 退出：遮罩淡入，卡片轻微上浮，时长取设计 Token */
.dialog-enter-active,
.dialog-leave-active {
  transition: opacity var(--duration-micro) ease;
}

.dialog-enter-active .dialog__card,
.dialog-leave-active .dialog__card {
  transition:
    opacity var(--duration-page) ease,
    transform var(--duration-page) cubic-bezier(0.2, 0.8, 0.2, 1);
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}

.dialog-enter-from .dialog__card,
.dialog-leave-to .dialog__card {
  opacity: 0;
  transform: translateY(8px) scale(0.985);
}

/* 靠上：从上方下落弹入 */
.dialog-enter-from .dialog__card--top,
.dialog-leave-to .dialog__card--top {
  transform: translateY(-18px) scale(0.985);
}

@media (max-width: 640px) {
  .dialog {
    align-items: flex-end;
    padding: 0;
  }

  /* 窄屏改底部面板：拇指可达，动效改为上滑 */
  .dialog__card {
    max-width: none;
    max-height: calc(100vh - var(--space10));
    border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  }

  .dialog-enter-from .dialog__card,
  .dialog-leave-to .dialog__card,
  .dialog-enter-from .dialog__card--top,
  .dialog-leave-to .dialog__card--top {
    transform: translateY(24px);
  }

  .dialog--top {
    align-items: flex-end;
    padding-top: 0;
  }

  .dialog__head {
    padding: var(--space4) var(--space4) var(--space3);
  }

  .dialog__body {
    padding: var(--space4);
  }

  .dialog__footer {
    padding: var(--space3) var(--space4) var(--space4);
  }
}

@media (prefers-reduced-motion: reduce) {
  .dialog-enter-active,
  .dialog-leave-active,
  .dialog-enter-active .dialog__card,
  .dialog-leave-active .dialog__card {
    transition: none;
  }

  .dialog-enter-from .dialog__card,
  .dialog-leave-to .dialog__card {
    transform: none;
  }
}
</style>
