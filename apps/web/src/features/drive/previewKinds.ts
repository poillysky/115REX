// 网盘可预览类型：只做浏览器原生能扛住的（图 / 音视频 / PDF / 文本），不做 Office。

export type PreviewKind = 'image' | 'video' | 'audio' | 'pdf' | 'text'

const IMAGE = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'svg', 'ico'])
const VIDEO = new Set(['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'ts', 'm2ts', 'webm', 'rmvb'])
const AUDIO = new Set(['mp3', 'flac', 'aac', 'wav', 'm4a', 'ogg', 'wma', 'opus'])
const PDF = new Set(['pdf'])
const TEXT = new Set([
  'txt',
  'md',
  'markdown',
  'json',
  'xml',
  'csv',
  'tsv',
  'log',
  'srt',
  'ass',
  'ssa',
  'vtt',
  'html',
  'htm',
  'css',
  'js',
  'mjs',
  'cjs',
  'ts',
  'tsx',
  'jsx',
  'vue',
  'py',
  'go',
  'rs',
  'java',
  'kt',
  'c',
  'h',
  'cpp',
  'hpp',
  'cs',
  'php',
  'rb',
  'sh',
  'bash',
  'zsh',
  'bat',
  'ps1',
  'yaml',
  'yml',
  'toml',
  'ini',
  'conf',
  'cfg',
  'env',
  'sql',
  'nfo',
])

/** 文本预览上限：超过则提示下载，避免大日志卡死页面 */
export const TEXT_PREVIEW_MAX_BYTES = 2 * 1024 * 1024

export function extOf(nameOrExt: string): string {
  const raw = (nameOrExt || '').toLowerCase().trim()
  if (!raw) return ''
  if (!raw.includes('.')) return raw.replace(/^\./, '')
  const base = raw.split(/[/\\]/).pop() || raw
  const idx = base.lastIndexOf('.')
  return idx >= 0 ? base.slice(idx + 1) : base
}

export function previewKindOf(extension: string, fileName = ''): PreviewKind | null {
  const ext = extOf(extension) || extOf(fileName)
  if (IMAGE.has(ext)) return 'image'
  if (VIDEO.has(ext)) return 'video'
  if (AUDIO.has(ext)) return 'audio'
  if (PDF.has(ext)) return 'pdf'
  if (TEXT.has(ext)) return 'text'
  return null
}

export function canPreview(extension: string, fileName = ''): boolean {
  return previewKindOf(extension, fileName) !== null
}
