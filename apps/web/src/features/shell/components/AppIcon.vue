<script setup lang="ts">
// 系统操作图标（docs/02 §7.2）：统一取 Phosphor 字形，Regular 为线性态、Fill 为实心态。
// 用法：<AppIcon name="search" />，尺寸由 .icon 的 20×20 决定，需要时用 size 覆盖。

import { computed } from 'vue'
import type { IconName } from './icon-names'

const props = withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 20 })

// 字形由 tools/gen-icons.mjs 从 @phosphor-icons/core 同步到 src/assets/icons，
// 这里以 ?raw 引入源码，构建期只打包用到的 SVG，运行时不发额外请求。
const RAW = import.meta.glob('@/assets/icons/*/*.svg', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>

// Phosphor 资源只含 <path>，viewBox 统一为 0 0 256 256
function drawing(weight: 'regular' | 'fill', name: string): string {
  const source = RAW[`/src/assets/icons/${weight}/${name}.svg`]
  return source?.match(/<path\b[^>]*>/g)?.join('') ?? ''
}

// IconName 是对外语义键，与 Phosphor 字形名不必同名；同一语义的线性态 / 实心态成对取自同一字形
const GLYPHS: Record<IconName, { regular: string; fill?: string }> = {
  search: { regular: 'magnifying-glass' },
  library: { regular: 'books' },
  settings: { regular: 'faders' },
  play: { regular: 'play', fill: 'play-fill' },
  pause: { regular: 'pause' },
  stop: { regular: 'stop' },
  record: { regular: 'record' },
  'skip-forward': { regular: 'skip-forward' },
  'skip-back': { regular: 'skip-back' },
  shuffle: { regular: 'shuffle' },
  repeat: { regular: 'repeat' },
  'repeat-once': { regular: 'repeat-once' },
  queue: { regular: 'queue' },
  playlist: { regular: 'playlist' },
  heart: { regular: 'heart' },
  'heart-filled': { regular: 'heart', fill: 'heart-fill' },
  download: { regular: 'arrow-line-down' },
  transfer: { regular: 'arrows-left-right' },
  folder: { regular: 'folder' },
  'chevron-left': { regular: 'caret-left' },
  'chevron-right': { regular: 'caret-right' },
  'chevron-down': { regular: 'caret-down' },
  close: { regular: 'x' },
  refresh: { regular: 'arrow-clockwise' },
  volume: { regular: 'speaker-high' },
  'volume-muted': { regular: 'speaker-slash' },
  fullscreen: { regular: 'corners-out' },
  'fullscreen-exit': { regular: 'corners-in' },
  alert: { regular: 'warning' },
  check: { regular: 'check' },
  film: { regular: 'film-strip' },
  clock: { regular: 'clock' },
  logout: { regular: 'sign-out' },
  link: { regular: 'link' },
  list: { regular: 'list' },
  grid: { regular: 'squares-four' },
  globe: { regular: 'globe' },
  bell: { regular: 'bell' },
  inbox: { regular: 'tray' },
  user: { regular: 'user' },
  tv: { regular: 'television' },
  sparkles: { regular: 'sparkle' },
  // 助手标记：与 GitHub 同属内联自绘，不走 Phosphor 资产同步
  robot: { regular: 'robot' },
  dashboard: { regular: 'house' },
  star: { regular: 'star' },
  compass: { regular: 'compass' },
  screen: { regular: 'monitor' },
  music: { regular: 'music-notes' },
  calendar: { regular: 'calendar-blank' },
  'cloud-down': { regular: 'cloud-arrow-down' },
  // 115 网盘品牌标记：Phosphor 无品牌字形，保留原手写路径，仅在 44px 白底板上使用
  p115: { regular: 'p115' },
  layers: { regular: 'stack' },
  puzzle: { regular: 'puzzle-piece' },
  image: { regular: 'image' },
  key: { regular: 'key' },
  sliders: { regular: 'sliders-horizontal' },
  copy: { regular: 'copy' },
  eye: { regular: 'eye' },
  'eye-off': { regular: 'eye-slash' },

  // 编辑与增删
  trash: { regular: 'trash' },
  edit: { regular: 'pencil-simple' },
  plus: { regular: 'plus' },
  minus: { regular: 'minus' },
  dots: { regular: 'dots-three' },
  'dots-vertical': { regular: 'dots-three-vertical' },
  save: { regular: 'floppy-disk' },

  // 状态与反馈
  'check-circle': { regular: 'check-circle' },
  'x-circle': { regular: 'x-circle' },
  'warning-circle': { regular: 'warning-circle' },
  info: { regular: 'info' },
  question: { regular: 'question' },
  'check-square': { regular: 'check-square' },
  'minus-square': { regular: 'minus-square' },
  'toggle-left': { regular: 'toggle-left' },
  'toggle-right': { regular: 'toggle-right' },
  'shield-check': { regular: 'shield-check' },
  'shield-warning': { regular: 'shield-warning' },
  lock: { regular: 'lock' },
  'lock-open': { regular: 'lock-open' },

  // 列表与筛选
  filter: { regular: 'funnel' },
  'filter-simple': { regular: 'funnel-simple' },
  'sort-ascending': { regular: 'sort-ascending' },
  'sort-descending': { regular: 'sort-descending' },
  'list-checks': { regular: 'list-checks' },
  'search-plus': { regular: 'magnifying-glass-plus' },
  'search-minus': { regular: 'magnifying-glass-minus' },
  tag: { regular: 'tag' },
  hash: { regular: 'hash' },
  bookmark: { regular: 'bookmark-simple' },
  flag: { regular: 'flag' },
  pin: { regular: 'push-pin' },
  sidebar: { regular: 'sidebar-simple' },

  // 传输与网络
  upload: { regular: 'upload-simple' },
  'download-simple': { regular: 'download-simple' },
  'upload-simple': { regular: 'upload-simple' },
  cloud: { regular: 'cloud' },
  'cloud-up': { regular: 'cloud-arrow-up' },
  wifi: { regular: 'wifi-high' },
  'wifi-off': { regular: 'wifi-slash' },
  'link-simple': { regular: 'link-simple' },
  'link-break': { regular: 'link-break' },
  'arrow-square-out': { regular: 'arrow-square-out' },
  'arrow-square-in': { regular: 'arrow-square-in' },
  share: { regular: 'share-network' },

  // 设备与存储
  'hard-drives': { regular: 'hard-drives' },
  'hard-drive': { regular: 'hard-drive' },
  database: { regular: 'database' },
  'device-mobile': { regular: 'device-mobile' },
  devices: { regular: 'devices' },
  desktop: { regular: 'desktop' },
  laptop: { regular: 'laptop' },
  cpu: { regular: 'cpu' },
  'graphics-card': { regular: 'graphics-card' },
  keyboard: { regular: 'keyboard' },
  mouse: { regular: 'mouse' },
  battery: { regular: 'battery-full' },
  gauge: { regular: 'gauge' },

  // 文件与文档
  'file-text': { regular: 'file-text' },
  'file-down': { regular: 'file-arrow-down' },
  'file-up': { regular: 'file-arrow-up' },
  clipboard: { regular: 'clipboard-text' },
  note: { regular: 'note-pencil' },
  ticket: { regular: 'ticket' },
  receipt: { regular: 'receipt' },
  paperclip: { regular: 'paperclip' },

  // 用户与账号
  'user-plus': { regular: 'user-plus' },
  users: { regular: 'users' },
  'users-three': { regular: 'users-three' },
  'id-card': { regular: 'identification-card' },
  at: { regular: 'at' },
  mail: { regular: 'envelope-simple' },
  send: { regular: 'paper-plane-tilt' },

  // 时间与图表
  timer: { regular: 'timer' },
  hourglass: { regular: 'hourglass' },
  'chart-line': { regular: 'chart-line' },
  'chart-bar': { regular: 'chart-bar' },
  'chart-pie': { regular: 'chart-pie-slice' },
  pulse: { regular: 'pulse' },
  target: { regular: 'target' },
  crosshair: { regular: 'crosshair-simple' },

  // 工具与开发
  wrench: { regular: 'wrench' },
  hammer: { regular: 'hammer' },
  gear: { regular: 'gear' },
  toolbox: { regular: 'toolbox' },
  terminal: { regular: 'terminal' },
  code: { regular: 'code' },
  brackets: { regular: 'brackets-curly' },
  'git-branch': { regular: 'git-branch' },
  'git-commit': { regular: 'git-commit' },
  'git-merge': { regular: 'git-merge' },
  'git-pull-request': { regular: 'git-pull-request' },
  flask: { regular: 'flask' },
  'test-tube': { regular: 'test-tube' },

  // 外观与环境
  rocket: { regular: 'rocket-launch' },
  flame: { regular: 'flame' },
  drop: { regular: 'drop' },
  wind: { regular: 'wind' },
  sun: { regular: 'sun' },
  moon: { regular: 'moon' },
  'cloud-rain': { regular: 'cloud-rain' },
  snowflake: { regular: 'snowflake' },
  palette: { regular: 'palette' },
  'paint-brush': { regular: 'paint-brush' },
  swatches: { regular: 'swatches' },
  cursor: { regular: 'cursor' },
  planet: { regular: 'planet' },

  // GitHub 品牌标记：Phosphor 无品牌字形，用官方 octicon 路径自绘，只在品牌位使用
  github: { regular: 'github' },
}

const FILLED = new Set<IconName>(['play', 'heart-filled', 'p115', 'github', 'robot'])

// 品牌字形自带 24×24 视野
const P115_PATH =
  'M12 5.6a4.4 4.4 0 0 0-4.4 4.4c0 1.1.4 2.1 1.1 2.8a4.15 4.15 0 0 0-1.6 3.3v.3c0 1.9 1.5 3.4 3.4 3.4 1.1 0 2-.5 2.6-1.3.6.8 1.5 1.3 2.6 1.3 1.9 0 3.4-1.5 3.4-3.4v-.3c0-1.3-.6-2.5-1.6-3.3.7-.7 1.1-1.7 1.1-2.8A4.4 4.4 0 0 0 12 5.6Z'

// GitHub mark 取自官方 octicons（primer/octicons，MIT），实心 24×24
const GITHUB_PATH =
  'M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23a11.5 11.5 0 0 1 3.003-.404c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.898-.015 3.293 0 .322.216.694.825.576C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12'

// 助手 mark：与 GitHub 同属 AppIcon 内联自绘（不走 Phosphor 同步），实心 24×24；外轮廓贴边并对齐 octicon 光学重量
const ROBOT_PATH =
  'M12 1c.8 0 1.5.7 1.5 1.5V4h5.25A3.25 3.25 0 0 1 22 7.25v11.5A3.25 3.25 0 0 1 18.75 22H5.25A3.25 3.25 0 0 1 2 18.75V7.25A3.25 3.25 0 0 1 5.25 4H10.5V2.5C10.5 1.7 11.2 1 12 1ZM7.75 8.5a1.75 1.75 0 1 0 0 3.5 1.75 1.75 0 0 0 0-3.5Zm8.5 0a1.75 1.75 0 1 0 0 3.5 1.75 1.75 0 0 0 0-3.5ZM6.5 15.5h4.75a1 1 0 1 1 0 2H6.5a1 1 0 1 1 0-2Zm6.25 0H17.5a1 1 0 1 1 0 2h-4.75a1 1 0 1 1 0-2Z'

const glyph = computed(() => {
  if (props.name === 'p115') return { box: '0 0 24 24', paths: `<path d="${P115_PATH}"/>` }
  if (props.name === 'github') return { box: '0 0 24 24', paths: `<path d="${GITHUB_PATH}"/>` }
  if (props.name === 'robot') return { box: '0 0 24 24', paths: `<path d="${ROBOT_PATH}"/>` }
  const map = GLYPHS[props.name]
  const weight = FILLED.has(props.name) ? 'fill' : 'regular'
  return { box: '0 0 256 256', paths: drawing(weight, map[weight] ?? map.regular) }
})
</script>

<template>
  <svg
    class="icon"
    :width="props.size"
    :height="props.size"
    :viewBox="glyph.box"
    aria-hidden="true"
    focusable="false"
    v-html="glyph.paths"
  />
</template>
