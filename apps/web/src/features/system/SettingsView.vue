﻿<script setup lang="ts">
// 设定（系统 → 设定）：版面参考 MoviePilot 的设置页——顶部一级 tab，卡片内左说明右内容，底部左右分置动作条。
// 参数全部在同一页展开，切 tab 只换卡片内容，不再是外层页 + 内嵌子页的套娃。
import { ref } from 'vue'

import SettingsPanel from '@/features/shell/components/SettingsPanel.vue'

import IconLibrarySettings from './IconLibrarySettings.vue'
import NetworkSettings from './NetworkSettings.vue'
import ServerSettings from './ServerSettings.vue'

/** 顶部一级 tab；设定只有一层页面，tab 只切卡片内容 */
const TABS = [
  { key: 'general', label: '系统设定' },
  { key: 'icons', label: '图标库' },
  { key: 'server', label: '服务端' },
] as const

type TabKey = (typeof TABS)[number]['key']

const tab = ref<TabKey>('general')

// 高级配置弹窗挂在页面里，由底部动作条触发
const advancedOpen = ref(false)
</script>

<template>
  <div class="settings">
    <SettingsPanel class="settings__panel">
      <nav class="tabs" role="tablist" aria-label="设定分组">
        <button
          v-for="item in TABS"
          :key="item.key"
          type="button"
          class="tab"
          :class="{ 'is-active': tab === item.key }"
          :aria-selected="tab === item.key"
          role="tab"
          @click="tab = item.key"
        >
          {{ item.label }}
        </button>
      </nav>

      <NetworkSettings v-if="tab === 'general'" v-model:advanced-open="advancedOpen" />
      <IconLibrarySettings v-else-if="tab === 'icons'" />
      <ServerSettings v-else />
    </SettingsPanel>
  </div>
</template>

<style scoped>
.settings {
  width: 100%;
}

.settings__panel {
  max-width: none;
  gap: var(--space4);
}

/* 顶栏一级 tab：等宽分段，贴齐内容栏宽，选中中性面（docs/02 §10） */
.tabs {
  display: flex;
  width: 100%;
  gap: var(--space1);
  padding: var(--space1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
  box-shadow: var(--shadow-card);
}

.tab {
  flex: 1;
  height: 36px;
  padding: 0 var(--space3);
  border-radius: var(--radius-md);
  border: 1px solid transparent;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
  transition:
    color var(--duration-micro) ease,
    background-color var(--duration-micro) ease,
    box-shadow var(--duration-micro) ease;
}

.tab:hover {
  color: var(--color-text-primary);
}

.tab.is-active {
  color: var(--color-text-primary);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.tab:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}
</style>
