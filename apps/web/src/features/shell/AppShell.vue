<script setup lang="ts">
// 应用外壳（docs/03 §2–§3）：顶栏 + 侧栏 + 内容区。
// 顶栏管全局信息（品牌、通知、账号），侧栏管页面入口；
// 内容区由这里统一限宽（默认与云下载同档 1280）并居中，页面自己不再加左右留白。
// 播放页 / 登录页走 bare 路由，不套外壳。
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/features/shell/AppHeader.vue'
import SideBar from '@/features/shell/SideBar.vue'

const route = useRoute()
/** 窄屏侧栏抽屉开关；宽屏侧栏常驻，这个值不生效。 */
const sidebarOpen = ref(false)

/** 内容宽度档位：路由用 meta.width 声明，未声明按正文宽档。 */
const contentMax = computed(() => {
  const width = route.meta.width
  if (width === 'narrow') return 'var(--content-narrow)'
  if (width === 'medium') return 'var(--content-medium)'
  return 'var(--content-wide)'
})

// 切页后收起抽屉，避免遮挡内容
watch(() => route.fullPath, () => {
  sidebarOpen.value = false
})
</script>

<template>
  <div class="shell">
    <a class="shell__skip" href="#main-content">跳到主要内容</a>
    <AppHeader @toggle-sidebar="sidebarOpen = !sidebarOpen" />
    <div class="shell__body">
      <SideBar :open="sidebarOpen" @navigate="sidebarOpen = false" @close="sidebarOpen = false" />
      <main id="main-content" class="shell__main" tabindex="-1">
        <div class="shell__content" :style="{ '--content-max': contentMax }">
          <RouterView v-slot="{ Component }">
            <Transition name="page" mode="out-in">
              <component :is="Component" :key="route.fullPath" />
            </Transition>
          </RouterView>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

/* 键盘用户的第一站：按 Tab 才出现，鼠标用户不会看到 */
.shell__skip {
  position: fixed;
  top: var(--space2);
  left: var(--space2);
  z-index: 100;
  padding: var(--space2) var(--space4);
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: var(--color-on-primary);
  box-shadow: var(--shadow-overlay);
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  transform: translateY(calc(-100% - var(--space4)));
  transition: transform var(--duration-micro) ease;
}

.shell__skip:focus-visible {
  transform: translateY(0);
}

.shell__main:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: -2px;
  border-radius: var(--radius-md);
}

.shell__body {
  display: flex;
  flex: 1;
  align-items: stretch;
  /* 内容台：Level 0 环境底，与实色 Chrome 形成明度差 */
  background: var(--color-background);
}

.shell__main {
  flex: 1;
  min-width: 0;
  padding: var(--space6) var(--space6) var(--space8);
  background: transparent;
}

/* 页面共享同一个内容框架：宽度上限 + 居中 + 统一内边距。
   页面只负责自己的垂直节奏，不再各自写左右 padding。 */
.shell__content {
  width: 100%;
  max-width: var(--content-max);
  margin-inline: auto;
}

/* 转场只做轻微的淡入上浮，不做整页缩放，避免大面积位移 */
.page-enter-active {
  transition:
    opacity calc(var(--duration-page) * 0.62) ease,
    transform calc(var(--duration-page) * 0.62) cubic-bezier(0.22, 1, 0.36, 1);
}

.page-leave-active {
  transition: opacity calc(var(--duration-micro) * 0.9) ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .shell__main {
    padding: var(--space4) var(--space4) var(--space8);
  }
}

@media (max-width: 640px) {
  .shell__main {
    padding: var(--space3) var(--space3) var(--space6);
  }
}

@media (prefers-reduced-motion: reduce) {
  .page-enter-active,
  .page-leave-active {
    transition: none;
  }

  .page-enter-from {
    transform: none;
  }
}
</style>
