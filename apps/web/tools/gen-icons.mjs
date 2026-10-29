// 同步 @phosphor-icons/core 中被 AppIcon 引用的字形到 src/assets/icons。
// 只搬用到的 SVG 源码，避免把 1500+ 字形整体打进 bundle。
// 触发：npm run icons（build 前置）。

import { copyFileSync, existsSync, mkdirSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const webRoot = join(here, '..')
const source = join(webRoot, 'node_modules/@phosphor-icons/core/assets')
const target = join(webRoot, 'src/assets/icons')

// 与 AppIcon.vue 的 GLYPHS 对应：IconName → Phosphor 字形名
const GLYPHS = {
  search: 'magnifying-glass',
  library: 'books',
  settings: 'faders',
  play: 'play',
  pause: 'pause',
  stop: 'stop',
  record: 'record',
  'skip-forward': 'skip-forward',
  'skip-back': 'skip-back',
  shuffle: 'shuffle',
  repeat: 'repeat',
  'repeat-once': 'repeat-once',
  queue: 'queue',
  playlist: 'playlist',
  heart: 'heart',
  'heart-filled': 'heart',
  download: 'arrow-line-down',
  transfer: 'arrows-left-right',
  folder: 'folder',
  'chevron-left': 'caret-left',
  'chevron-right': 'caret-right',
  'chevron-down': 'caret-down',
  close: 'x',
  refresh: 'arrow-clockwise',
  volume: 'speaker-high',
  'volume-muted': 'speaker-slash',
  fullscreen: 'corners-out',
  'fullscreen-exit': 'corners-in',
  alert: 'warning',
  check: 'check',
  film: 'film-strip',
  clock: 'clock',
  logout: 'sign-out',
  link: 'link',
  list: 'list',
  grid: 'squares-four',
  globe: 'globe',
  bell: 'bell',
  inbox: 'tray',
  user: 'user',
  tv: 'television',
  sparkles: 'sparkle',
  dashboard: 'house',
  star: 'star',
  compass: 'compass',
  screen: 'monitor',
  music: 'music-notes',
  calendar: 'calendar-blank',
  'cloud-down': 'cloud-arrow-down',
  layers: 'stack',
  puzzle: 'puzzle-piece',
  image: 'image',
  key: 'key',
  sliders: 'sliders-horizontal',
  copy: 'copy',
  eye: 'eye',
  'eye-off': 'eye-slash',

  // 编辑与增删
  trash: 'trash',
  edit: 'pencil-simple',
  plus: 'plus',
  minus: 'minus',
  dots: 'dots-three',
  'dots-vertical': 'dots-three-vertical',
  save: 'floppy-disk',

  // 状态与反馈
  'check-circle': 'check-circle',
  'x-circle': 'x-circle',
  'warning-circle': 'warning-circle',
  info: 'info',
  question: 'question',
  'check-square': 'check-square',
  'minus-square': 'minus-square',
  'toggle-left': 'toggle-left',
  'toggle-right': 'toggle-right',
  'shield-check': 'shield-check',
  'shield-warning': 'shield-warning',
  lock: 'lock',
  'lock-open': 'lock-open',

  // 列表与筛选
  filter: 'funnel',
  'filter-simple': 'funnel-simple',
  'sort-ascending': 'sort-ascending',
  'sort-descending': 'sort-descending',
  'list-checks': 'list-checks',
  'search-plus': 'magnifying-glass-plus',
  'search-minus': 'magnifying-glass-minus',
  tag: 'tag',
  hash: 'hash',
  bookmark: 'bookmark-simple',
  flag: 'flag',
  pin: 'push-pin',
  sidebar: 'sidebar-simple',

  // 传输与网络
  upload: 'upload-simple',
  'download-simple': 'download-simple',
  'upload-simple': 'upload-simple',
  cloud: 'cloud',
  'cloud-up': 'cloud-arrow-up',
  wifi: 'wifi-high',
  'wifi-off': 'wifi-slash',
  'link-simple': 'link-simple',
  'link-break': 'link-break',
  'arrow-square-out': 'arrow-square-out',
  'arrow-square-in': 'arrow-square-in',
  share: 'share-network',

  // 设备与存储
  'hard-drives': 'hard-drives',
  'hard-drive': 'hard-drive',
  database: 'database',
  'device-mobile': 'device-mobile',
  devices: 'devices',
  desktop: 'desktop',
  laptop: 'laptop',
  cpu: 'cpu',
  'graphics-card': 'graphics-card',
  keyboard: 'keyboard',
  mouse: 'mouse',
  battery: 'battery-full',
  gauge: 'gauge',

  // 文件与文档
  'file-text': 'file-text',
  'file-down': 'file-arrow-down',
  'file-up': 'file-arrow-up',
  clipboard: 'clipboard-text',
  note: 'note-pencil',
  ticket: 'ticket',
  receipt: 'receipt',
  paperclip: 'paperclip',

  // 用户与账号
  'user-plus': 'user-plus',
  users: 'users',
  'users-three': 'users-three',
  'id-card': 'identification-card',
  at: 'at',
  mail: 'envelope-simple',
  send: 'paper-plane-tilt',

  // 时间与图表
  timer: 'timer',
  hourglass: 'hourglass',
  'chart-line': 'chart-line',
  'chart-bar': 'chart-bar',
  'chart-pie': 'chart-pie-slice',
  pulse: 'pulse',
  target: 'target',
  crosshair: 'crosshair-simple',

  // 工具与开发
  wrench: 'wrench',
  hammer: 'hammer',
  gear: 'gear',
  toolbox: 'toolbox',
  terminal: 'terminal',
  code: 'code',
  brackets: 'brackets-curly',
  'git-branch': 'git-branch',
  'git-commit': 'git-commit',
  'git-merge': 'git-merge',
  'git-pull-request': 'git-pull-request',
  flask: 'flask',
  'test-tube': 'test-tube',

  // 外观与环境
  rocket: 'rocket-launch',
  flame: 'flame',
  drop: 'drop',
  wind: 'wind',
  sun: 'sun',
  moon: 'moon',
  'cloud-rain': 'cloud-rain',
  snowflake: 'snowflake',
  palette: 'palette',
  'paint-brush': 'paint-brush',
  swatches: 'swatches',
  cursor: 'cursor',
  planet: 'planet',
}

rmSync(target, { recursive: true, force: true })
for (const weight of ['regular', 'fill']) {
  mkdirSync(join(target, weight), { recursive: true })
}

const missing = new Set()
let copied = 0
for (const file of Object.values(GLYPHS)) {
  for (const weight of ['regular', 'fill']) {
    const from = join(source, weight, `${file}.svg`)
    if (!existsSync(from)) {
      if (weight === 'regular') missing.add(file)
      continue
    }
    copyFileSync(from, join(target, weight, `${file}.svg`))
    copied += 1
  }
}

if (missing.size) {
  console.error(`缺少字形：${[...missing].join(', ')}`)
  process.exit(1)
}
console.log(`icons: 已同步 ${copied} 个 SVG 到 src/assets/icons`)
