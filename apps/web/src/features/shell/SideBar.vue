<script setup lang="ts">
// 侧栏（docs/03 §3）：所有页面入口都在这里，宽屏常驻、窄屏抽屉。
// 导航只有一层：每个入口都是可直接点击的链接，二级项与一级平铺，不做折叠。
// 顶栏只放全局信息，不放页面入口，避免两处导航打架。
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppIcon from '@/features/shell/components/AppIcon.vue'
import type { IconName } from '@/features/shell/components/icon-names'

defineProps<{ open: boolean }>()
const emit = defineEmits<{ navigate: []; close: [] }>()

const route = useRoute()

interface NavItem {
  name: string
  label: string
  icon: IconName
}

/** 按分区组织：分区标题 caption + 500，不加字距、不做分隔线（docs/02 §9.2） */
const GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: '总览',
    items: [
      { name: 'index', label: '仪表盘', icon: 'dashboard' },
      { name: 'discover-movie', label: '影视', icon: 'film' },
      { name: 'discover-drama', label: '短剧', icon: 'tv' },
      { name: 'discover-girl', label: '小姐姐', icon: 'sparkles' },
    ],
  },
  {
    title: '整理',
    items: [
      { name: 'drive-files', label: '文件浏览', icon: 'folder' },
      { name: 'drive-cloud', label: '云下载', icon: 'cloud-down' },
      { name: 'flows-organize', label: '文件整理', icon: 'layers' },
      { name: 'flows-workflow', label: '自动化工作流', icon: 'transfer' },
    ],
  },
  {
    title: '系统',
    items: [
      { name: 'system-115', label: '网盘管理', icon: 'globe' },
      { name: 'system-plugins', label: '插件管理', icon: 'puzzle' },
      { name: 'system-settings', label: '设定', icon: 'settings' },
    ],
  },
]

/** 详情页属于影视的一支；播放页按来路归属，这里统一落到仪表盘 */
const DETAIL_PARENT = 'discover-movie'

/** 当前页：库详情 / 元数据详情都归到影视，其余取路由名 */
const activeName = computed(() =>
  route.name === 'detail' || route.name === 'meta-detail'
    ? DETAIL_PARENT
    : String(route.name ?? ''),
)
</script>

<template>
  <aside class="sidebar" :class="{ 'is-open': open }">
    <nav class="sidebar__nav" aria-label="页面导航">
      <div v-for="group in GROUPS" :key="group.title" class="sidebar__group">
        <p class="sidebar__label">{{ group.title }}</p>

        <RouterLink
          v-for="item in group.items"
          :key="item.name"
          class="sidebar__item"
          :class="{ 'is-active': activeName === item.name }"
          :to="{ name: item.name }"
          :aria-current="activeName === item.name ? 'page' : undefined"
          @click="emit('navigate')"
        >
          <AppIcon :name="item.icon" :size="19" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </div>
    </nav>
  </aside>

  <div v-if="open" class="sidebar__scrim" @click="emit('close')" />
</template>

<style scoped>
.sidebar {
  position: sticky;
  top: var(--topbar-height);
  z-index: 20;
  display: flex;
  flex-direction: column;
  flex: none;
  width: var(--sidebar-width);
  height: calc(100vh - var(--topbar-height));
  padding: var(--space3) var(--space3) var(--space4);
  /* 实色导航架：右侧投影把内容台推开，和顶栏同属 Chrome 层 */
  background: var(--chrome-surface);
  box-shadow: var(--shadow-chrome-side);
  overflow: hidden;
}

.sidebar__nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow-y: auto;
  padding-bottom: var(--space2);
}

.sidebar__group {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

/* 分区标题：caption + 500，不加字距、不加大写、不做分隔线（docs/02 §9.2） */
.sidebar__label {
  margin: var(--space5) 0 var(--space2);
  padding: 0 var(--space3);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  line-height: 1.6;
  color: var(--color-text-tertiary);
}

.sidebar__group:first-child .sidebar__label {
  margin-top: var(--space1);
}

/* 条目：线性图标 + label 字阶，行高 38，圆角卡片式选中面 */
.sidebar__item {
  display: flex;
  align-items: center;
  gap: var(--space3);
  height: 38px;
  padding: 0 var(--space3);
  border-radius: var(--radius-md);
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.sidebar__item :deep(.icon) {
  color: var(--color-text-tertiary);
  transition: color var(--duration-micro) ease;
}

.sidebar__item:hover {
  background: color-mix(in srgb, var(--color-surface-secondary) 76%, transparent);
  color: var(--color-text-primary);
}

.sidebar__item:hover :deep(.icon) {
  color: var(--color-text-secondary);
}

/* 选中态：中性灰 pill；在实色侧栏上用 surfaceSecondary 才读得出层级（docs/02 §9.2） */
.sidebar__item.is-active {
  color: var(--color-text-primary);
  font-weight: var(--font-heading3-weight);
  background: var(--color-surface-secondary);
  box-shadow: inset 0 0 0 1px var(--panel-border);
}

.sidebar__item.is-active :deep(.icon) {
  color: var(--color-text-primary);
}

.sidebar__scrim {
  display: none;
}

/* 中档以下：侧栏改成抽展层，由顶栏的菜单按钮控制 */
@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    top: var(--topbar-height);
    left: 0;
    z-index: 25;
    height: calc(100vh - var(--topbar-height));
    background: var(--color-surface);
    box-shadow: var(--shadow-overlay);
    transform: translateX(-100%);
    transition: transform var(--duration-page) cubic-bezier(0.22, 1, 0.36, 1);
  }
  .sidebar.is-open {
    transform: translateX(0);
  }
  /* 触屏抽屉：行高放大到舒适点击区 */
  .sidebar__item {
    height: 44px;
  }
  .sidebar__scrim {
    position: fixed;
    inset: var(--topbar-height) 0 0;
    z-index: 24;
    display: block;
    background: color-mix(in srgb, var(--color-text-primary) 30%, transparent);
    backdrop-filter: blur(2px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar {
    transition: none;
  }
}
</style>
