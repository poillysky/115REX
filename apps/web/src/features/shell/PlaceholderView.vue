<script setup lang="ts">
// 占位页（docs/03 §3）：新导航已铺开、功能尚未接入，先用一句说明交代后续会放什么。
// 真实页面落地后逐个替换，不再保留占位。
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'

const route = useRoute()
const router = useRouter()

/** 当前占位的是哪一屏：标题取路由 meta，导航与文档标题保持同一措辞。 */
const label = computed(() => String(route.meta.title ?? '这一屏'))
const isHome = computed(() => route.name === 'index')

/** 占位不等于死路：给一个已经可用的下一步，用户不会停在空白里。 */
function goNext(): void {
  void router.push({ name: isHome.value ? 'system-115' : 'index' })
}

function goSettings(): void {
  void router.push({ name: 'system-settings' })
}
</script>

<template>
  <div class="placeholder">
    <section class="placeholder__card">
      <span class="placeholder__icon" aria-hidden="true">
        <AppIcon name="sparkles" :size="26" />
      </span>
      <h2 class="placeholder__title">{{ label }}尚未实现</h2>
      <p class="placeholder__desc">
        这一屏的功能还在规划中，先把导航与页面骨架定下来，接入后内容会出现在这里。
      </p>
      <div class="placeholder__actions">
        <AppButton variant="primary" @click="goNext">
          {{ isHome ? '打开 115 网盘' : '回到仪表盘' }}
        </AppButton>
        <AppButton variant="ghost" @click="goSettings">前往设定</AppButton>
      </div>
    </section>
  </div>
</template>

<style scoped>
.placeholder {
  display: grid;
  place-items: center;
  min-height: 64vh;
  padding: var(--space8) 0;
}

/* 占位卡：实色 Level 1，无外投影；中性图标底，不铺品牌渐变（docs/02 §5.2 / §7.4） */
.placeholder__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  max-width: 540px;
  padding: var(--space10) var(--space8);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  text-align: center;
}

.placeholder__icon {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  margin-bottom: var(--space5);
  border-radius: var(--radius-xl);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.placeholder__title {
  font-size: var(--font-heading2-size);
  font-weight: var(--font-heading2-weight);
  letter-spacing: var(--font-heading2-tracking);
  line-height: 1.3;
  color: var(--color-text-primary);
}

.placeholder__desc {
  max-width: 42ch;
  margin-top: var(--space2);
  font-size: var(--font-caption-size);
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.placeholder__actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space2);
  flex-wrap: wrap;
  margin-top: var(--space6);
}

@media (max-width: 640px) {
  .placeholder {
    min-height: 56vh;
    padding: var(--space6) 0;
  }

  .placeholder__card {
    padding: var(--space8) var(--space5);
    border-radius: var(--radius-xl);
  }
}
</style>
