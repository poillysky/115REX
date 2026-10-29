// 纯展示规则：格式化与状态文案。不依赖框架，不写 UI。

export function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes <= 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value >= 100 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds <= 0) return '—'
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`
}

export function formatDate(epochSeconds: number | null): string {
  if (!epochSeconds) return '—'
  const date = new Date(epochSeconds * 1000)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(
    date.getDate(),
  ).padStart(2, '0')}`
}

/** 文件列表修改时间：同年用 MM-DD HH:mm，跨年带年份 */
export function formatFileTime(epochSeconds: number | null, now = new Date()): string {
  if (!epochSeconds) return '—'
  const date = new Date(epochSeconds * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`
  const day = `${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  if (date.getFullYear() === now.getFullYear()) return `${day} ${time}`
  return `${date.getFullYear()}-${day} ${time}`
}

/** 相对时间：刚同步 / N 分钟前 / 今天 HH:MM / 年月日 */
export function formatRelative(epochSeconds: number | null, now = Date.now()): string {
  if (!epochSeconds) return '—'
  const then = epochSeconds * 1000
  const delta = Math.max(0, now - then)
  const minute = 60_000
  const hour = 60 * minute
  if (delta < minute) return '刚刚'
  if (delta < hour) return `${Math.floor(delta / minute)} 分钟前`
  if (delta < 24 * hour) return `${Math.floor(delta / hour)} 小时前`
  return formatDate(epochSeconds)
}

export function progressRatio(position: number, duration: number | null): number {
  if (!duration || duration <= 0) return 0
  return Math.min(1, Math.max(0, position / duration))
}

const SOURCE_STATUS_TEXT: Record<string, string> = {
  ok: '正常',
  timeout: '超时',
  error: '出错',
  circuit_open: '已熔断',
  disabled: '已禁用',
}

export function sourceStatusText(status: string): string {
  return SOURCE_STATUS_TEXT[status] ?? status
}

const ACTION_STATUS_TEXT: Record<string, string> = {
  pending: '待处理',
  running: '执行中',
  succeeded: '已转存',
  failed: '失败',
  cancelled: '已取消',
}

export function actionStatusText(status: string): string {
  return ACTION_STATUS_TEXT[status] ?? status
}

const BINDING_STATUS_TEXT: Record<string, string> = {
  healthy: '正常',
  expiring: '即将失效',
  expired: '已失效',
  unbound: '未绑定',
}

export function bindingStatusText(status: string): string {
  return BINDING_STATUS_TEXT[status] ?? status
}

export const COMPLETENESS_TEXT: Record<string, string> = {
  full: '完整',
  partial: '不完整',
  unknown: '未知',
}
