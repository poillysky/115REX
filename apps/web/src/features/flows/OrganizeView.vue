<script setup lang="ts">
// 文件整理：顶部一级 tab；转存路径从网盘管理迁入，作为默认首 tab。
import { ref } from 'vue'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import SettingsPanel from '@/features/shell/components/SettingsPanel.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'

const TABS = [
  { key: 'path', label: '转存路径' },
  { key: 'rules', label: '整理规则' },
] as const

type TabKey = (typeof TABS)[number]['key']

const tab = ref<TabKey>('path')
</script>

<template>
  <div class="organize">
    <SettingsPanel class="organize__panel">
      <nav class="tabs" role="tablist" aria-label="文件整理分组">
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

      <SysStyles v-if="tab === 'path'">
        <section class="group">
          <div class="group__head">
            <h2 class="group__title">转存路径</h2>
            <p class="group__desc">资源转存到 115 时写入的默认目录，后续可从网盘目录树中选择。</p>
          </div>
          <div class="group__body">
            <div class="path">
              <span class="path__icon" aria-hidden="true">
                <AppIcon name="folder" :size="18" />
              </span>
              <div class="path__main">
                <span class="path__label">默认转存目录</span>
                <span class="path__value path__value--empty">尚未配置</span>
              </div>
              <AppButton size="sm" disabled title="目录选择器尚未开放">选择目录</AppButton>
            </div>
            <p class="path__note">此配置暂未接入，保存与目录浏览会在后续版本开放。</p>
          </div>
        </section>
      </SysStyles>

      <AppEmptyState
        v-else
        title="整理规则尚未接入"
        description="媒体刮削、命名与目录映射会放在这里。"
        icon="folder"
      />
    </SettingsPanel>
  </div>
</template>

<style scoped>
.organize {
  width: 100%;
}

.organize__panel {
  max-width: none;
  gap: var(--space4);
}

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

.path {
  display: flex;
  align-items: center;
  gap: var(--space3);
  min-height: 56px;
  padding: var(--space3) var(--space5);
}

.path__icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

.path__main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.path__label {
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.path__value {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.path__value--empty {
  font-family: inherit;
  color: var(--color-text-tertiary);
}

.path__note {
  margin: 0;
  padding: var(--space3) var(--space5);
  border-top: 1px solid var(--panel-divider);
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
  line-height: 1.5;
}
</style>
