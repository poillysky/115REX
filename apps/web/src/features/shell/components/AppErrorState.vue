<script setup lang="ts">
// 错误态（docs/02 §10 AppErrorState / 03 §6）：说明原因 + 可重试，不暴露错误码。
import AppButton from '@/features/shell/components/AppButton.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'

withDefaults(defineProps<{ message: string; retryLabel?: string }>(), { retryLabel: '重试' })

const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="error" role="alert">
    <AppIcon name="alert" :size="22" class="error__icon" />
    <p class="error__text">{{ message }}</p>
    <AppButton size="sm" @click="emit('retry')">{{ retryLabel }}</AppButton>
  </div>
</template>

<style scoped>
.error {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space4);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  border: 1px solid color-mix(in srgb, var(--color-danger) 22%, var(--panel-border));
  box-shadow: var(--shadow-card);
}

.error__icon {
  color: var(--color-danger);
}

.error__text {
  flex: 1;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}
</style>
