// 插件头像：
// - 内置插件：只认打包进仓库的本地 Logo，运行时零外网请求
// - 市场插件：才走「设定 · 图标库」远程索引
import { preferencesApi } from '@/data/api'
import type { PluginItem } from '@/domain/contract'

import bangumiIcon from '@/assets/plugin-icons/bangumi.svg'
import doubanIcon from '@/assets/plugin-icons/douban.svg'
import fanartIcon from '@/assets/plugin-icons/fanart.svg'
import tmdbIcon from '@/assets/plugin-icons/tmdb.svg'

/** 内置插件 id → 本地品牌 Logo（Vite 打包进产物，不联网） */
const BUILTIN_ICONS: Record<string, string> = {
  themoviedb: tmdbIcon,
  douban: doubanIcon,
  bangumi: bangumiIcon,
  fanart: fanartIcon,
}

/** 市场插件匹配图标库时的别名（内置不用） */
const MARKET_ALIASES: Record<string, string[]> = {}

function normalize(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/\.(png|jpe?g|webp|svg|gif)$/i, '')
    .replace(/[\s_\-.]+/g, '')
}

function queryKeys(plugin: PluginItem): string[] {
  const keys = new Set<string>()
  for (const raw of [plugin.name, plugin.id, plugin.author, ...(MARKET_ALIASES[plugin.id] ?? [])]) {
    const key = normalize(raw)
    if (key) keys.add(key)
  }
  return [...keys]
}

function basenameKey(url: string): string {
  try {
    const path = new URL(url).pathname
    const file = path.split('/').pop() || ''
    return normalize(decodeURIComponent(file))
  } catch {
    return normalize(url.split('/').pop() || '')
  }
}

/** 内置插件本地头像；非内置或未收录返回空串。 */
export function localPluginIconUrl(plugin: PluginItem): string {
  if (!plugin.builtin) return ''
  return BUILTIN_ICONS[plugin.id] ?? ''
}

type IconLibraryRef = { url: string; enabled: boolean }

/** 市场插件用：摊平已启用图标库。内置页不应调用。 */
export async function loadIconIndex(
  libraries?: IconLibraryRef[],
): Promise<Map<string, string>> {
  const enabled = (
    libraries ??
    (await preferencesApi.get()).iconLibraries
  ).filter((item) => item.enabled)

  const chunks = await Promise.all(
    enabled.map(async (library) => {
      try {
        return await preferencesApi.iconLibraryIcons(library.url)
      } catch {
        return []
      }
    }),
  )

  const index = new Map<string, string>()
  function put(key: string, url: string): void {
    if (key && !index.has(key)) index.set(key, url)
  }
  for (const entries of chunks) {
    for (const entry of entries) {
      put(normalize(entry.name), entry.url)
      put(basenameKey(entry.url), entry.url)
    }
  }
  return index
}

/** 解析头像：内置强制本地；其余才查图标库索引。 */
export function resolvePluginIconUrl(index: Map<string, string>, plugin: PluginItem): string {
  const local = localPluginIconUrl(plugin)
  if (local) return local
  if (plugin.builtin) return ''

  const keys = queryKeys(plugin)
  for (const key of keys) {
    const url = index.get(key)
    if (url) return url
  }
  const ranked = [...keys].sort((a, b) => b.length - a.length)
  for (const [name, url] of index) {
    for (const key of ranked) {
      if (key.length >= 4 && (name.includes(key) || key.includes(name))) return url
    }
  }
  return ''
}
