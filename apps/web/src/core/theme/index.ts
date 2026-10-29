// 主题适配层。色值只有一个来源：tokens.generated（由 design-tokens 生成）。
// 手动主题（明暗 + 强调色）持久化在本地，首帧由 index.html 的内联脚本先读一次，避免刷新闪白。

import { ref } from 'vue'

import {
  colorDark,
  colorLight,
  themeAccents,
  type ThemeAccent,
  type ThemeMode,
} from '@/core/theme/tokens.generated'

export type { ThemeAccent, ThemeMode }

export const DEFAULT_MODE: ThemeMode = 'light'
export const DEFAULT_ACCENT: ThemeAccent = 'default'

const MODE_KEY = 'rex.themeMode'
const ACCENT_KEY = 'rex.themeAccent'
const MODES: readonly ThemeMode[] = ['light', 'dark']
const ACCENTS = Object.keys(themeAccents) as ThemeAccent[]

export interface ThemePreference {
  mode: ThemeMode
  accent: ThemeAccent
}

/** 全局唯一主题状态：切换后所有用到它的页面一起更新。 */
export const themePreference = ref<ThemePreference>({ mode: DEFAULT_MODE, accent: DEFAULT_ACCENT })

function readLocal(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeLocal(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    /* 隐私模式下忽略 */
  }
}

/** 首次访问跟随系统，之后一律以用户选过的为准。 */
export function systemMode(): ThemeMode {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function loadTheme(): ThemePreference {
  const storedMode = readLocal(MODE_KEY)
  const storedAccent = readLocal(ACCENT_KEY)
  return {
    mode: MODES.includes(storedMode as ThemeMode) ? (storedMode as ThemeMode) : systemMode(),
    accent: ACCENTS.includes(storedAccent as ThemeAccent)
      ? (storedAccent as ThemeAccent)
      : DEFAULT_ACCENT,
  }
}

/** 把主题写到 <html> 上：CSS 变量与 color-scheme 都从这里取值。 */
export function applyTheme(preference: ThemePreference): void {
  const root = document.documentElement
  root.dataset.theme = preference.mode
  root.dataset.accent = preference.accent
  // 浏览器原生控件（滚动条、表单、日期选择）跟着一起切
  root.style.colorScheme = preference.mode
}

export function saveTheme(preference: ThemePreference): void {
  writeLocal(MODE_KEY, preference.mode)
  writeLocal(ACCENT_KEY, preference.accent)
}

/** 启动时调用一次；之后由主题管理页切换。 */
export function initTheme(): ThemePreference {
  const preference = loadTheme()
  setTheme(preference)
  return preference
}

/** 切换主题：写 <html>、持久化并同步全局状态。 */
export function setTheme(preference: ThemePreference): void {
  applyTheme(preference)
  saveTheme(preference)
  themePreference.value = preference
}

/** 主题名到展示文案，页面与文档共用一处。 */
export function accentLabel(accent: ThemeAccent): string {
  return themeAccents[accent].label
}

/** 需要 JS 侧取色时用这里，不要在组件里写裸色值。 */
export function color(role: keyof typeof colorLight): string {
  return (document.documentElement.dataset.theme === 'dark' ? colorDark : colorLight)[role]
}
