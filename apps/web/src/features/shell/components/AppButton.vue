<script setup lang="ts">
// 按钮角色（docs/02 §10 AppButton）。四种变体：primary / secondary / ghost / danger。
// 主按钮在 Web 用 radiusLg 而非胶囊（胶囊只属 iOS 主按钮形态），文字走 label 档。

withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'md' | 'sm'
    disabled?: boolean
    loading?: boolean
    type?: 'button' | 'submit' | 'reset'
    /** 关联同 id 的表单，用于把页脚动作条接回卡片里的表单 */
    form?: string
  }>(),
  { variant: 'secondary', size: 'md', disabled: false, loading: false, type: 'button', form: undefined },
)
</script>

<template>
  <button
    :type="type"
    :form="form"
    class="btn"
    :class="[`btn--${variant}`, `btn--${size}`]"
    :disabled="disabled || loading"
    :aria-busy="loading"
  >
    <span v-if="loading" class="btn__spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space2);
  /* 常规按钮 radiusLg；胶囊形态只属 iOS 主按钮（docs/02 §5.1 / §10） */
  border-radius: var(--radius-lg);
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  white-space: nowrap;
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease,
    border-color var(--duration-micro) ease,
    transform var(--duration-micro) ease;
}

.btn:active:not(:disabled) {
  transform: translateY(1px);
}

.btn--md {
  min-height: 40px;
  padding: 0 var(--space4);
}

.btn--sm {
  min-height: 32px;
  padding: 0 var(--space3);
  font-size: var(--font-caption-size);
  border-radius: var(--radius-md);
}

/* 主操作：单色 primary（docs/02 §10）；轻内高光，外投影克制，不做渐变底。 */
.btn--primary {
  background: var(--color-primary);
  color: var(--color-on-primary);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / 0.16),
    0 1px 2px color-mix(in srgb, var(--color-primary) 18%, transparent),
    0 6px 14px color-mix(in srgb, var(--color-primary) 16%, transparent);
}
.btn--primary:hover {
  background: color-mix(in srgb, var(--color-primary) 88%, #000);
}

.btn--secondary {
  background: var(--color-surface);
  color: var(--color-text-primary);
  border: 1px solid var(--panel-border);
  box-shadow: inset 0 1px 0 var(--highlight-line);
}
.btn--secondary:hover:not(:disabled) {
  background: var(--color-surface-secondary);
  border-color: color-mix(in srgb, var(--color-text-tertiary) 45%, var(--panel-border));
}

.btn--ghost {
  color: var(--color-text-secondary);
}
.btn--ghost:hover:not(:disabled) {
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
}

/* 破坏性确认：填充语义红。文字取 surface —— 浅色下为白，深色下自然转为深字，两边都过对比度 */
.btn--danger {
  background: var(--color-danger);
  color: var(--color-surface);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.16);
}
.btn--danger:hover:not(:disabled) {
  background: color-mix(in srgb, var(--color-danger) 88%, #000);
}

/* 禁用态保持可读：中性底 + 次要文字色，不再整体降透明度 */
.btn:disabled {
  background: var(--color-surface-secondary);
  border-color: transparent;
  box-shadow: none;
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.btn--secondary:disabled {
  background: var(--color-surface-secondary);
  border-color: var(--color-border-soft);
}

.btn__spinner {
  width: 14px;
  height: 14px;
  border-radius: var(--radius-full);
  border: 2px solid currentColor;
  border-top-color: transparent;
  animation: btn-spin calc(var(--duration-page) * 2.4) linear infinite;
}

@keyframes btn-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
