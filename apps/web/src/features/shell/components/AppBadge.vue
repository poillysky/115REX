<script setup lang="ts">
// 状态标签（docs/02 §10 AppStatusBadge / §7）。颜色只用语义色，形状统一胶囊。
// 不单靠颜色传达状态：标签始终带文字。

withDefaults(
  defineProps<{
    tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'primary'
  }>(),
  { tone: 'neutral' },
)
</script>

<template>
  <span class="badge" :class="`badge--${tone}`">
    <slot />
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space1);
  height: 22px;
  padding: 0 var(--space2);
  border-radius: var(--radius-full);
  font-size: var(--font-caption-size);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

/* 状态标签只表达语义，不承担"强调品牌"的职责 */
.badge--primary {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.badge--success {
  color: var(--color-success);
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
}

.badge--warning {
  color: var(--color-warning);
  background: color-mix(in srgb, var(--color-warning) 14%, transparent);
}

.badge--danger {
  color: var(--color-danger);
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
}
</style>
