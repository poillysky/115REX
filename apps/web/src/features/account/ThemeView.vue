<script setup lang="ts">
// 主题管理（账号管理 → 主题管理）：明暗模式 + 强调色。
// 切换即时生效并写入本地；强调色只覆盖品牌三色，色值全部来自 design-tokens，页面里不写裸色。
import { computed, onMounted } from 'vue'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import {
  accentLabel,
  initTheme,
  setTheme,
  systemMode,
  themePreference,
  type ThemeAccent,
  type ThemeMode,
} from '@/core/theme'
import { colorDark, colorLight, themeAccents } from '@/core/theme/tokens.generated'

const MODE_OPTIONS: { key: ThemeMode; label: string; desc: string; icon: 'screen' | 'sparkles' }[] = [
  { key: 'light', label: '浅色', desc: '白天与强光环境下更清晰', icon: 'screen' },
  { key: 'dark', label: '深色', desc: '夜间降低屏幕整体亮度', icon: 'sparkles' },
]

const ACCENTS = Object.keys(themeAccents) as ThemeAccent[]
const PALETTE = { light: colorLight, dark: colorDark }

/** 缩略预览取被预览那套主题的面色，而不是当前主题的面色。 */
function previewStyle(target: ThemeMode): Record<string, string> {
  const palette = PALETTE[target]
  return {
    background: palette.surface,
    borderColor: palette.separator,
    '--mode-line': palette.separator,
  }
}

// 直接读写全局主题状态，顶栏、按钮、焦点环会跟着一起变
const mode = computed(() => themePreference.value.mode)
const accent = computed(() => themePreference.value.accent)
const system = systemMode()

const savedHint = computed(() => {
  const modeLabel = MODE_OPTIONS.find((item) => item.key === mode.value)?.label ?? ''
  return `当前：${modeLabel} · ${accentLabel(accent.value)}`
})

function select(nextMode: ThemeMode, nextAccent: ThemeAccent): void {
  setTheme({ mode: nextMode, accent: nextAccent })
}

/** 回到跟随系统：只重置明暗，强调色保留用户的选择。 */
function followSystem(): void {
  select(system, accent.value)
}

onMounted(() => {
  // 刷新后直接进本页（或从别的入口切进来）时，用已存偏好覆盖首帧猜测值
  initTheme()
})
</script>

<template>
  <div class="theme">
    <!-- 明暗模式 -->
    <section class="group">
      <div class="group__head">
        <h2 class="group__title">外观</h2>
        <p class="group__desc">默认跟随系统；手动选过之后以这里为准，刷新不会丢。</p>
      </div>
      <div class="group__body">
        <div class="cards cards--modes" role="radiogroup" aria-label="明暗模式">
          <button
            v-for="item in MODE_OPTIONS"
            :key="item.key"
            type="button"
            class="mode"
            :class="[`mode--${item.key}`, { 'is-active': mode === item.key }]"
            role="radio"
            :aria-checked="mode === item.key"
            @click="select(item.key, accent)"
          >
            <!-- 缩略预览：只用水色块表示明暗，不画整页截图 -->
            <span class="mode__preview" :style="previewStyle(item.key)" aria-hidden="true">
              <span class="mode__preview-bar" />
              <span class="mode__preview-line" />
              <span class="mode__preview-line mode__preview-line--short" />
            </span>
            <span class="mode__body">
              <span class="mode__name">
                <AppIcon :name="item.icon" :size="15" />
                {{ item.label }}
              </span>
              <span class="mode__desc">{{ item.desc }}</span>
            </span>
            <AppIcon v-if="mode === item.key" class="mode__check" name="check" :size="16" />
          </button>
        </div>
      </div>
    </section>

    <!-- 强调色 -->
    <section class="group">
      <div class="group__head">
        <h2 class="group__title">强调色</h2>
        <p class="group__desc">用于主按钮、选中态与焦点环；浅色和深色下各有一套色值。</p>
      </div>
      <div class="group__body">
        <div class="cards cards--accents" role="radiogroup" aria-label="强调色">
          <button
            v-for="key in ACCENTS"
            :key="key"
            type="button"
            class="accent"
            :class="{ 'is-active': accent === key }"
            role="radio"
            :aria-checked="accent === key"
            @click="select(mode, key)"
          >
            <span
              class="accent__swatch"
              :style="{
                background: themeAccents[key][mode].primary,
                color: themeAccents[key][mode].onPrimary,
              }"
              aria-hidden="true"
            >
              <AppIcon v-if="accent === key" name="check" :size="15" />
            </span>
            <span class="accent__name">{{ accentLabel(key) }}</span>
          </button>
        </div>
      </div>
    </section>

    <div class="theme__foot">
      <p class="theme__state">{{ savedHint }}</p>
      <AppButton v-if="mode !== system" size="sm" @click="followSystem">
        跟随系统（{{ system === 'dark' ? '深色' : '浅色' }}）
      </AppButton>
    </div>
  </div>
</template>

<style scoped>
.theme {
  display: flex;
  flex-direction: column;
  gap: var(--space5);
  /* 宽度与内边距由 AppShell 统一处理 */
  padding: 0;
}

/* 说明在卡片上方，卡片吃掉整行宽度（与账号页一致） */
.group {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
}

.group__head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--space1);
}

.group__title {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  letter-spacing: var(--font-heading3-tracking);
  line-height: 1.3;
}

.group__desc {
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.group__body {
  padding: var(--space5);
  border-radius: var(--radius-xl);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.cards {
  display: grid;
  gap: var(--space3);
}

.cards--modes {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.cards--accents {
  grid-template-columns: repeat(auto-fill, minmax(112px, 1fr));
}

/* 选中只换中性底与描边，不用品牌色整块铺开 */
.mode,
.accent {
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  transition:
    border-color var(--duration-micro) ease,
    background-color var(--duration-micro) ease;
}

.mode:hover,
.accent:hover {
  border-color: var(--color-text-tertiary);
}

.mode.is-active,
.accent.is-active {
  border-color: var(--color-text-primary);
  background: var(--color-surface-secondary);
  box-shadow: inset 0 1px 0 var(--highlight-line);
}

.mode {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  padding: var(--space2);
  text-align: left;
}

/* 缩略预览：面色与分隔线由 previewStyle 按被预览的主题注入 */
.mode__preview {
  display: flex;
  flex-direction: column;
  gap: var(--space1);
  min-height: 72px;
  padding: var(--space3);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-soft);
}

.mode__preview-bar {
  width: 28%;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
}

.mode__preview-line {
  height: 5px;
  border-radius: var(--radius-full);
  background: var(--mode-line);
}

.mode__preview-line--short {
  width: 62%;
}

.mode__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--space1) var(--space1);
}

.mode__name {
  display: inline-flex;
  align-items: center;
  gap: var(--space1);
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
}

.mode__desc {
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.mode__check {
  position: absolute;
  top: var(--space2);
  right: var(--space2);
  padding: 2px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

.accent {
  display: flex;
  align-items: center;
  gap: var(--space2);
  padding: var(--space2) var(--space3);
  text-align: left;
}

/* 色点颜色由模板按当前明暗从 tokens 取，不在样式里写死 */
.accent__swatch {
  display: grid;
  place-items: center;
  flex: none;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
}

.accent__name {
  font-size: var(--font-label-size);
}

.theme__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  padding: 0 var(--space1);
}

.theme__state {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

@media (max-width: 720px) {
  .cards--modes {
    grid-template-columns: minmax(0, 1fr);
  }

  .cards--accents {
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  }
}
</style>
