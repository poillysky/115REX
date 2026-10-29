<script setup lang="ts">
// 空态（docs/02 §10 AppEmptyState / 03 §6）：一句说明 + 一个主要动作。
// 中性面 + 线性图标，不铺品牌渐变，不抢主操作焦点。
import AppIcon from '@/features/shell/components/AppIcon.vue'

withDefaults(
  defineProps<{
    title: string
    description?: string
    icon?: 'search' | 'film' | 'folder' | 'alert' | 'clock' | 'compass' | 'puzzle'
  }>(),
  { description: '', icon: 'search' },
)
</script>

<template>
  <div class="empty">
    <div class="empty__icon">
      <AppIcon :name="icon" :size="26" />
    </div>
    <p class="empty__title">{{ title }}</p>
    <p v-if="description" class="empty__desc">{{ description }}</p>
    <div v-if="$slots.default" class="empty__action">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space2);
  padding: var(--space10) var(--space8);
  text-align: center;
  border-radius: var(--radius-xl);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

/* 线性图标 + 淡品牌底晕，空态不铺 brandGradient（docs/02 §7.4） */
.empty__icon {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  margin-bottom: var(--space2);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.empty__title {
  font-size: var(--font-label-size);
  font-weight: 600;
  color: var(--color-text-primary);
}

.empty__desc {
  font-size: var(--font-caption-size);
  line-height: 1.7;
  color: var(--color-text-secondary);
  max-width: 44ch;
}

.empty__action {
  margin-top: var(--space3);
}

@media (max-width: 640px) {
  .empty {
    padding: var(--space8) var(--space5);
    border-radius: var(--radius-xl);
  }
}
</style>
