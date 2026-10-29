<script setup lang="ts">
// 插件管理：已安装（含内置） / 插件库（市场海报墙）。市场配置收进弹窗。
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'

import { useNotifyStore } from '@/application/notify'
import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppEmptyState from '@/features/shell/components/AppEmptyState.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import type { IconName } from '@/features/shell/components/icon-names'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import SettingsPanel from '@/features/shell/components/SettingsPanel.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'
import { describeError } from '@/core/api/error'
import { pluginsApi, preferencesApi } from '@/data/api'
import type { PluginConfig } from '@/data/api'
import type { PluginItem } from '@/domain/contract'
import {
  loadIconIndex,
  localPluginIconUrl,
  resolvePluginIconUrl,
} from '@/features/system/pluginIcons'

/** 需要填写 API Key 的内置插件 */
const API_KEY_PLUGINS = new Set(['themoviedb'])

/** 图标库未命中时的 AppIcon 兜底 */
const PLUGIN_ICONS: Record<string, IconName> = {
  themoviedb: 'film',
  douban: 'star',
  bangumi: 'calendar',
  fanart: 'image',
}

const TABS = [
  { key: 'builtin', label: '内置' },
  { key: 'installed', label: '已安装' },
  { key: 'market', label: '插件库' },
] as const

type TabKey = (typeof TABS)[number]['key']

const notify = useNotifyStore()

const tab = ref<TabKey>('builtin')
const loading = ref(true)
const errorText = ref('')
const saving = ref(false)
const saveError = ref('')
const configOpen = ref(false)
/** 当前打开三点菜单的插件 id */
const menuId = ref<string | null>(null)
/** 菜单挂到 body，用固定坐标避免被卡片裁切 */
const menuPos = ref({ top: 0, left: 0 })
const menuEl = ref<HTMLElement | null>(null)
/** 设置弹窗中的插件 */
const settingsPlugin = ref<PluginItem | null>(null)
const settingsLoading = ref(false)
const settingsSaving = ref(false)
const settingsError = ref('')
const settingsApiKey = ref('')
const savedSettings = ref<PluginConfig>({ enabled: true, apiKey: '' })

const menuPlugin = computed(
  () => installed.value.find((item) => item.id === menuId.value) ?? null,
)

const settingsNeedsApiKey = computed(
  () => Boolean(settingsPlugin.value && API_KEY_PLUGINS.has(settingsPlugin.value.id)),
)

const settingsDirty = computed(() => {
  if (!settingsPlugin.value || !settingsNeedsApiKey.value) return false
  return settingsApiKey.value !== savedSettings.value.apiKey
})

const installed = ref<PluginItem[]>([])
const marketPlugins = ref<PluginItem[]>([])
/** 设定 · 图标库摊平索引：规范化名 → 图片地址 */
const iconIndex = ref<Map<string, string>>(new Map())

const marketText = ref('')
const autoReload = ref(false)
const savedMarketText = ref('')
const savedAutoReload = ref(false)

const dirty = computed(
  () => marketText.value !== savedMarketText.value || autoReload.value !== savedAutoReload.value,
)

const marketRepos = computed(() =>
  marketText.value
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean),
)

const savedMarketCount = computed(
  () =>
    savedMarketText.value
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean).length,
)

/** 内置：出厂元数据源；已安装：从市场装上的；插件库：可浏览安装 */
const builtinPlugins = computed(() => installed.value.filter((item) => item.builtin))
const installedExtras = computed(() => installed.value.filter((item) => !item.builtin))
const cardPlugins = computed(() => {
  if (tab.value === 'builtin') return builtinPlugins.value
  if (tab.value === 'installed') return installedExtras.value
  return []
})
const cardEnabledCount = computed(() => cardPlugins.value.filter((item) => item.enabled).length)

/** 海报墙只展示非内置市场插件 */
const marketWall = computed(() => marketPlugins.value.filter((item) => !item.builtin))

function iconOf(plugin: PluginItem): IconName {
  return PLUGIN_ICONS[plugin.id] ?? 'puzzle'
}

/** 内置本地打包；已安装用服务端落盘 iconUrl；市场预览才可能走远程/图标库。 */
function libraryIconUrl(plugin: PluginItem): string {
  if (plugin.builtin) return localPluginIconUrl(plugin)
  if (plugin.iconUrl) return plugin.iconUrl
  return resolvePluginIconUrl(iconIndex.value, plugin)
}

/** 卡片横幅底色：内置固定色相，其余按 id 哈希 */
const ACCENT: Record<string, string> = {
  themoviedb: '205 78% 36%',
  douban: '148 48% 30%',
  bangumi: '338 55% 36%',
  fanart: '262 42% 38%',
}

function accentOf(plugin: PluginItem): string {
  if (ACCENT[plugin.id]) return ACCENT[plugin.id]
  let hash = 0
  for (const ch of plugin.id) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0
  return `${hash % 360} 38% 36%`
}

async function loadPlugins(): Promise<void> {
  const [installedRes, marketRes] = await Promise.all([
    pluginsApi.installed(),
    pluginsApi.market(),
  ])
  installed.value = installedRes.plugins
  marketPlugins.value = marketRes.plugins
}

async function loadPrefs() {
  const prefs = await preferencesApi.get()
  const market = prefs.plugins.market.join('\n')
  marketText.value = market
  savedMarketText.value = market
  autoReload.value = prefs.plugins.autoReload
  savedAutoReload.value = prefs.plugins.autoReload
  return prefs
}

/** 图标库走外网，不挡首屏；内置插件用本地 Logo，无需等索引。 */
function loadIconsInBackground(libraries?: { url: string; enabled: boolean }[]): void {
  void loadIconIndex(libraries)
    .then((index) => {
      iconIndex.value = index
    })
    .catch(() => {
      iconIndex.value = new Map()
    })
}

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const [, prefs] = await Promise.all([loadPlugins(), loadPrefs()])
    // 已安装图标安装时已落盘；仅市场预览缺 iconUrl 时才临时查图标库
    const needsLibraryIcons = marketPlugins.value.some(
      (item) => !item.builtin && !item.iconUrl,
    )
    if (needsLibraryIcons) loadIconsInBackground(prefs.iconLibraries)
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

function closeMenu(): void {
  menuId.value = null
}

function placeMenu(anchor: HTMLElement): void {
  const rect = anchor.getBoundingClientRect()
  const width = 176
  const left = Math.min(
    Math.max(8, rect.right - width),
    window.innerWidth - width - 8,
  )
  menuPos.value = {
    top: Math.round(rect.bottom + 6),
    left: Math.round(left),
  }
}

async function toggleMenu(pluginId: string, event: MouseEvent): Promise<void> {
  if (menuId.value === pluginId) {
    closeMenu()
    return
  }
  const anchor = event.currentTarget
  if (!(anchor instanceof HTMLElement)) return
  placeMenu(anchor)
  menuId.value = pluginId
  await nextTick()
  placeMenu(anchor)
}

/** Teleport 到 body 后，需在 document 捕获外部点击才能收回 */
function onDocPointerDown(event: PointerEvent): void {
  if (!menuId.value) return
  const target = event.target
  if (!(target instanceof Node)) {
    closeMenu()
    return
  }
  if (menuEl.value?.contains(target)) return
  // 三点按钮交给 toggleMenu，避免 pointerdown 先关、click 又开
  if (target instanceof Element && target.closest('.plugin-card__menu-btn')) return
  closeMenu()
}

function onDocKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && menuId.value) closeMenu()
}

function onWindowReposition(): void {
  if (!menuId.value) return
  closeMenu()
}

async function openSettings(plugin: PluginItem): Promise<void> {
  closeMenu()
  settingsPlugin.value = plugin
  settingsError.value = ''
  settingsLoading.value = true
  settingsApiKey.value = ''
  savedSettings.value = { enabled: plugin.enabled, apiKey: '' }
  try {
    const config = await pluginsApi.config(plugin.id)
    settingsApiKey.value = config.apiKey
    savedSettings.value = { enabled: config.enabled, apiKey: config.apiKey }
  } catch (error) {
    settingsError.value = describeError(error)
  } finally {
    settingsLoading.value = false
  }
}

const installBusyId = ref<string | null>(null)

/** 安装：服务端立刻把远程图标落到本地，之后「已安装」只读本地图。 */
async function installFromMarket(plugin: PluginItem): Promise<void> {
  if (plugin.builtin || plugin.installed || installBusyId.value) return
  installBusyId.value = plugin.id
  try {
    const saved = await pluginsApi.install({
      id: plugin.id,
      name: plugin.name,
      author: plugin.author,
      version: plugin.version,
      description: plugin.description,
      kind: plugin.kind,
      capability: plugin.capability,
      homepage: plugin.homepage,
      repoUrl: plugin.repoUrl,
      labels: plugin.labels,
      iconUrl: plugin.iconUrl,
    })
    installed.value = [
      ...installed.value.filter((item) => item.id !== saved.id),
      saved,
    ]
    marketPlugins.value = marketPlugins.value.map((item) =>
      item.id === saved.id ? { ...item, installed: true, iconUrl: saved.iconUrl || item.iconUrl } : item,
    )
    notify.success(`已安装 ${saved.name}`)
    tab.value = 'installed'
  } catch (error) {
    notify.failure(describeError(error))
  } finally {
    installBusyId.value = null
  }
}

async function uninstallPlugin(plugin: PluginItem): Promise<void> {
  if (plugin.builtin) return
  closeMenu()
  try {
    await pluginsApi.uninstall(plugin.id)
    installed.value = installed.value.filter((item) => item.id !== plugin.id)
    marketPlugins.value = marketPlugins.value.map((item) =>
      item.id === plugin.id ? { ...item, installed: false } : item,
    )
    notify.success(`已卸载 ${plugin.name}`)
  } catch (error) {
    notify.failure(describeError(error))
  }
}

function closeSettings(): void {
  settingsPlugin.value = null
  settingsError.value = ''
}

async function saveSettings(): Promise<void> {
  const plugin = settingsPlugin.value
  if (!plugin || !settingsDirty.value || settingsSaving.value) return
  settingsSaving.value = true
  settingsError.value = ''
  try {
    const saved = await pluginsApi.saveConfig(plugin.id, {
      apiKey: settingsApiKey.value.trim(),
    })
    savedSettings.value = { enabled: saved.enabled, apiKey: saved.apiKey }
    settingsApiKey.value = saved.apiKey
    notify.success('已保存插件设置')
    closeSettings()
  } catch (error) {
    settingsError.value = describeError(error)
  } finally {
    settingsSaving.value = false
  }
}

function openConfig(): void {
  marketText.value = savedMarketText.value
  autoReload.value = savedAutoReload.value
  saveError.value = ''
  configOpen.value = true
}

function resetMarket(): void {
  marketText.value = savedMarketText.value
  autoReload.value = savedAutoReload.value
  saveError.value = ''
}

async function saveMarket(): Promise<void> {
  if (!dirty.value || saving.value) return
  saving.value = true
  saveError.value = ''
  try {
    const prefs = await preferencesApi.savePlugins({
      market: marketRepos.value,
      autoReload: autoReload.value,
    })
    const market = prefs.plugins.market.join('\n')
    marketText.value = market
    savedMarketText.value = market
    autoReload.value = prefs.plugins.autoReload
    savedAutoReload.value = prefs.plugins.autoReload
    configOpen.value = false
    notify.success('已保存插件库配置')
  } catch (error) {
    saveError.value = describeError(error)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
  document.addEventListener('pointerdown', onDocPointerDown, true)
  document.addEventListener('keydown', onDocKeydown)
  window.addEventListener('resize', onWindowReposition)
  window.addEventListener('scroll', onWindowReposition, true)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDocPointerDown, true)
  document.removeEventListener('keydown', onDocKeydown)
  window.removeEventListener('resize', onWindowReposition)
  window.removeEventListener('scroll', onWindowReposition, true)
})
</script>

<template>
  <div class="plugins">
    <SettingsPanel class="plugins__panel">
      <nav class="tabs" role="tablist" aria-label="插件管理分组">
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

      <AppErrorState v-if="errorText" :message="errorText" @retry="() => load()" />

      <div v-else-if="loading" class="plugins__skel plugins__skel--poster">
        <AppSkeleton v-for="n in 6" :key="n" height="168px" />
      </div>

      <SysStyles v-else-if="tab === 'builtin' || tab === 'installed'">
        <header v-if="cardPlugins.length" class="plugins__summary tabular">
          共 {{ cardPlugins.length }} 个 · 启用 {{ cardEnabledCount }}
        </header>
        <div v-if="cardPlugins.length" class="plugin-grid">
          <article
            v-for="plugin in cardPlugins"
            :key="plugin.id"
            class="plugin-card"
            :class="{ 'is-off': !plugin.enabled, 'is-menu-open': menuId === plugin.id }"
            :style="{ '--plugin-accent': accentOf(plugin) }"
          >
            <div class="plugin-card__banner">
              <div class="plugin-card__glow" aria-hidden="true" />
              <div class="plugin-card__title-row">
                <span
                  class="plugin-card__dot"
                  :class="plugin.enabled ? 'is-on' : 'is-off'"
                  :title="plugin.enabled ? '已启用' : '已停用'"
                />
                <h3 class="plugin-card__title">{{ plugin.name }}</h3>
                <span class="plugin-card__ver tabular">v{{ plugin.version }}</span>
              </div>
              <div class="plugin-card__mid">
                <p class="plugin-card__desc">{{ plugin.description }}</p>
                <div class="plugin-card__icon" aria-hidden="true">
                  <img
                    v-if="libraryIconUrl(plugin)"
                    class="plugin-card__img"
                    :src="libraryIconUrl(plugin)"
                    alt=""
                    loading="lazy"
                  />
                  <AppIcon v-else :name="iconOf(plugin)" :size="30" />
                </div>
              </div>
            </div>
            <footer class="plugin-card__foot">
              <div class="plugin-card__foot-start">
                <AppBadge v-if="plugin.builtin" tone="primary">内置</AppBadge>
              </div>
              <div class="plugin-card__menu-wrap" @click.stop>
                <button
                  type="button"
                  class="plugin-card__menu-btn"
                  :class="{ 'is-open': menuId === plugin.id }"
                  title="更多"
                  aria-haspopup="menu"
                  :aria-expanded="menuId === plugin.id"
                  :aria-label="`${plugin.name} 更多操作`"
                  @click="toggleMenu(plugin.id, $event)"
                >
                  <AppIcon name="dots-vertical" :size="16" />
                </button>
              </div>
            </footer>
          </article>
        </div>
        <AppEmptyState
          v-else-if="tab === 'builtin'"
          title="暂无内置插件"
          description="出厂元数据源会显示在这里。"
          icon="puzzle"
        />
        <AppEmptyState
          v-else
          title="还没有已安装的插件"
          description="从「插件库」安装的扩展会出现在这里。内置源请到「内置」查看。"
          icon="puzzle"
        >
          <AppButton size="sm" variant="primary" @click="tab = 'market'">去插件库</AppButton>
        </AppEmptyState>
      </SysStyles>

      <SysStyles v-else>
        <header class="plugins__toolbar">
          <p class="plugins__summary tabular">
            {{ marketWall.length ? `共 ${marketWall.length} 个插件` : '市场插件' }}
            <span v-if="savedMarketCount" class="plugins__summary-muted">
              · 已配置 {{ savedMarketCount }} 个源
            </span>
          </p>
          <AppButton size="sm" @click="openConfig">
            <AppIcon name="settings" :size="14" />
            市场配置
          </AppButton>
        </header>

        <div v-if="marketWall.length" class="poster-grid">
          <article v-for="plugin in marketWall" :key="plugin.id" class="poster-card">
            <div class="poster-card__cover" aria-hidden="true">
              <img
                v-if="libraryIconUrl(plugin)"
                class="poster-card__img"
                :src="libraryIconUrl(plugin)"
                alt=""
                loading="lazy"
              />
              <span v-else class="poster-card__fallback">
                <AppIcon name="puzzle" :size="28" />
              </span>
            </div>
            <div class="poster-card__body">
              <div class="poster-card__head">
                <h3 class="poster-card__title">{{ plugin.name }}</h3>
                <AppBadge v-if="plugin.installed" tone="success">已装</AppBadge>
              </div>
              <p class="poster-card__desc">{{ plugin.description }}</p>
              <div class="poster-card__meta">
                <span>{{ plugin.author || '未知作者' }}</span>
                <span class="tabular">v{{ plugin.version }}</span>
              </div>
              <AppButton
                v-if="!plugin.installed"
                size="sm"
                variant="primary"
                class="poster-card__install"
                :loading="installBusyId === plugin.id"
                @click="installFromMarket(plugin)"
              >
                安装
              </AppButton>
            </div>
          </article>
        </div>
        <AppEmptyState
          v-else
          title="插件库还是空的"
          description="配置市场地址后，可安装的插件会以海报墙展示。内置源请到「内置」查看。"
          icon="puzzle"
        >
          <AppButton size="sm" variant="primary" @click="openConfig">配置市场</AppButton>
        </AppEmptyState>
      </SysStyles>
    </SettingsPanel>

    <Teleport to="body">
      <div
        v-if="menuPlugin"
        ref="menuEl"
        class="plugin-card__menu"
        role="menu"
        :style="{ top: `${menuPos.top}px`, left: `${menuPos.left}px` }"
      >
        <button type="button" role="menuitem" @click="openSettings(menuPlugin)">
          <AppIcon name="gear" :size="15" />
          <span>设置</span>
        </button>
        <button
          v-if="!menuPlugin.builtin"
          type="button"
          role="menuitem"
          class="is-danger"
          @click="uninstallPlugin(menuPlugin)"
        >
          <AppIcon name="trash" :size="15" />
          <span>卸载</span>
        </button>
      </div>
    </Teleport>

    <AppDialog
      :open="Boolean(settingsPlugin)"
      :title="settingsPlugin ? `${settingsPlugin.name} · 设置` : '插件设置'"
      :description="settingsPlugin?.description || ''"
      size="md"
      @update:open="(open) => { if (!open) closeSettings() }"
    >
      <div
        v-if="settingsPlugin"
        class="plugin-settings"
        :style="{ '--plugin-accent': accentOf(settingsPlugin) }"
      >
        <div class="plugin-settings__identity">
          <div class="plugin-settings__mark" aria-hidden="true">
            <img
              v-if="libraryIconUrl(settingsPlugin)"
              class="plugin-settings__mark-img"
              :src="libraryIconUrl(settingsPlugin)"
              alt=""
            />
            <AppIcon v-else :name="iconOf(settingsPlugin)" :size="22" />
          </div>
          <div class="plugin-settings__identity-text">
            <div class="plugin-settings__identity-row">
              <span class="plugin-settings__identity-name">{{ settingsPlugin.name }}</span>
              <AppBadge v-if="settingsPlugin.builtin" tone="primary">内置</AppBadge>
            </div>
            <p class="plugin-settings__identity-meta tabular">
              v{{ settingsPlugin.version }}
              <span v-if="settingsPlugin.author"> · {{ settingsPlugin.author }}</span>
            </p>
          </div>
        </div>

        <div v-if="settingsLoading" class="plugin-settings__loading">
          <AppSkeleton height="88px" />
        </div>
        <template v-else>
          <section v-if="settingsNeedsApiKey" class="plugin-settings__panel">
            <header class="plugin-settings__panel-head">
              <span class="plugin-settings__panel-icon" aria-hidden="true">
                <AppIcon name="key" :size="16" />
              </span>
              <div class="plugin-settings__panel-copy">
                <h3 class="plugin-settings__panel-title">API Key</h3>
                <p class="plugin-settings__panel-desc">用于请求 TMDB 元数据的访问凭证</p>
              </div>
            </header>
            <label class="plugin-settings__field">
              <span class="sr-only">API Key</span>
              <input
                v-model="settingsApiKey"
                class="plugin-settings__input"
                type="password"
                autocomplete="off"
                spellcheck="false"
                placeholder="粘贴 themoviedb.org 申请的 API Key"
              />
            </label>
            <a
              class="plugin-settings__link"
              href="https://www.themoviedb.org/settings/api"
              target="_blank"
              rel="noopener noreferrer"
            >
              <AppIcon name="link" :size="13" />
              在 TMDB 申请 API Key
            </a>
          </section>

          <div v-else class="plugin-settings__empty">
            <AppIcon name="check" :size="18" />
            <p>该插件暂无额外参数</p>
          </div>

          <p v-if="settingsError" class="plugin-settings__error">{{ settingsError }}</p>
        </template>
      </div>
      <template #footer>
        <div class="config__footer">
          <AppButton size="sm" :disabled="settingsSaving" @click="closeSettings">取消</AppButton>
          <div class="config__footer-right">
            <AppButton
              size="sm"
              variant="primary"
              :loading="settingsSaving"
              :disabled="!settingsDirty || settingsLoading"
              @click="saveSettings"
            >
              保存
            </AppButton>
          </div>
        </div>
      </template>
    </AppDialog>

    <AppDialog
      v-model:open="configOpen"
      title="市场配置"
      description="扩展插件仓库地址；多个地址换行或逗号分隔，顺序即查找优先级。"
      size="md"
    >
      <div class="config">
        <label class="field">
          <span class="field__label">市场地址</span>
          <textarea
            v-model="marketText"
            class="field__textarea field__textarea--market"
            rows="5"
            placeholder="https://github.com/jxxghp/MoviePilot-Plugins"
            spellcheck="false"
          />
        </label>
        <div class="config__panel">
          <label class="switch-row">
            <span class="switch-row__text">
              <span class="switch-row__label">插件热加载</span>
              <span class="switch-row__hint">保存配置后自动重载已安装插件（扩展运行时接入后生效）</span>
            </span>
            <label class="switch" title="插件热加载">
              <input v-model="autoReload" type="checkbox" aria-label="插件热加载" />
              <span class="switch__track" aria-hidden="true" />
            </label>
          </label>
        </div>
        <p v-if="saveError" class="field__hint field__hint--error">{{ saveError }}</p>
      </div>
      <template #footer>
        <div class="config__footer">
          <AppButton size="sm" :disabled="!dirty || saving" @click="resetMarket">重置</AppButton>
          <div class="config__footer-right">
            <AppButton size="sm" @click="configOpen = false">取消</AppButton>
            <AppButton
              size="sm"
              variant="primary"
              :loading="saving"
              :disabled="!dirty"
              @click="saveMarket"
            >
              保存
            </AppButton>
          </div>
        </div>
      </template>
    </AppDialog>
  </div>
</template>

<style scoped>
.plugins {
  width: 100%;
}

.plugins__panel {
  max-width: none;
  gap: var(--space4);
}

.plugins__skel {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space2);
}

.plugins__skel--poster {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.plugins__summary {
  margin: 0 0 2px;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.plugins__summary-muted {
  color: var(--color-text-tertiary);
  opacity: 0.85;
}

.plugins__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  margin-bottom: 2px;
}

.plugins__toolbar .plugins__summary {
  margin: 0;
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

.plugin-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space3);
}

/* MoviePilot 风格：层次横幅 + 作者栏；图标裸露 contain */
.plugin-card {
  --plugin-accent: 220 28% 36%;
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  /* 允许三点菜单向下溢出；圆角裁切交给 banner / foot */
  overflow: visible;
  border: 1px solid color-mix(in srgb, hsl(var(--plugin-accent)) 22%, var(--panel-border));
  border-radius: calc(var(--radius-lg) + 2px);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  transition:
    opacity 180ms ease,
    transform 180ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 180ms ease,
    border-color 180ms ease;
}

.plugin-card.is-menu-open {
  z-index: 6;
}

.plugin-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, hsl(var(--plugin-accent)) 42%, var(--panel-border));
  box-shadow:
    var(--shadow-card),
    0 12px 28px color-mix(in srgb, hsl(var(--plugin-accent)) 22%, transparent);
}

/* 停用：不用整卡 opacity，避免菜单/弹窗叠上去发虚看不清 */
.plugin-card.is-off {
  border-color: color-mix(in srgb, var(--panel-border) 88%, transparent);
  box-shadow: none;
}

.plugin-card.is-off .plugin-card__banner {
  filter: grayscale(0.35) saturate(0.7);
}

.plugin-card.is-off .plugin-card__banner::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: rgb(255 255 255 / 10%);
}

.plugin-card.is-off .plugin-card__desc,
.plugin-card.is-off .plugin-card__title {
  opacity: 0.78;
}

.plugin-card.is-off .plugin-card__icon {
  opacity: 0.72;
  filter: drop-shadow(0 2px 6px rgb(0 0 0 / 28%)) grayscale(0.2);
}

.plugin-card.is-off:hover {
  transform: none;
  box-shadow: var(--shadow-card);
}

.plugin-card__banner {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 128px;
  padding: 14px 14px 12px;
  color: #fff;
  overflow: hidden;
  border-radius: calc(var(--radius-lg) + 1px) calc(var(--radius-lg) + 1px) 0 0;
  background:
    linear-gradient(165deg, rgb(0 0 0 / 18%) 0%, rgb(0 0 0 / 48%) 100%),
    linear-gradient(
      135deg,
      hsl(var(--plugin-accent) / 1) 0%,
      hsl(var(--plugin-accent) / 0.78) 48%,
      hsl(var(--plugin-accent) / 0.55) 100%
    );
}

.plugin-card__glow {
  position: absolute;
  inset: auto -20% -55% 35%;
  height: 90%;
  z-index: 0;
  pointer-events: none;
  background: radial-gradient(
    closest-side,
    hsl(var(--plugin-accent) / 0.55) 0%,
    transparent 72%
  );
  filter: blur(2px);
}

.plugin-card__title-row,
.plugin-card__mid {
  position: relative;
  z-index: 1;
}

.plugin-card__title-row {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
}

.plugin-card__dot {
  flex: none;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 0 2px rgb(255 255 255 / 22%);
}

.plugin-card__dot.is-on {
  background: #34d399;
  box-shadow:
    0 0 0 2px rgb(255 255 255 / 22%),
    0 0 10px rgb(52 211 153 / 55%);
}

.plugin-card__dot.is-off {
  background: rgb(255 255 255 / 38%);
}

.plugin-card__title {
  margin: 0;
  min-width: 0;
  flex: 1;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
  line-height: 1.25;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-shadow: 0 1px 3px rgb(0 0 0 / 40%);
}

.plugin-card__ver {
  flex: none;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  color: rgb(255 255 255 / 88%);
  background: rgb(255 255 255 / 12%);
  border: 1px solid rgb(255 255 255 / 14%);
}

.plugin-card__mid {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

.plugin-card__desc {
  margin: 0;
  flex: 1;
  min-width: 0;
  align-self: flex-start;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
  font-size: 12.5px;
  line-height: 1.5;
  color: rgb(255 255 255 / 90%);
  text-shadow: 0 1px 2px rgb(0 0 0 / 32%);
}

/* 统一底板：盒尺寸一致 + 内边距，抵消各品牌素材留白差异 */
.plugin-card__icon {
  flex: none;
  align-self: flex-end;
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  padding: 8px;
  box-sizing: border-box;
  overflow: hidden;
  border-radius: 12px;
  color: #1a1a1a;
  background: #fff;
  box-shadow:
    0 1px 0 rgb(255 255 255 / 55%) inset,
    0 3px 10px rgb(0 0 0 / 28%);
  transition: transform 180ms cubic-bezier(0.22, 1, 0.36, 1);
}

.plugin-card:hover .plugin-card__icon {
  transform: translateY(-2px) scale(1.04);
}

.plugin-card__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  display: block;
  pointer-events: none;
}

.plugin-card__icon :deep(.icon) {
  width: 28px;
  height: 28px;
}

.plugin-card__foot {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 42px;
  padding: 8px 10px 8px 12px;
  border-radius: 0 0 calc(var(--radius-lg) + 1px) calc(var(--radius-lg) + 1px);
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--color-surface-secondary) 55%, var(--color-surface)) 0%,
      var(--color-surface) 100%
    );
  border-top: 1px solid color-mix(in srgb, var(--panel-border) 85%, transparent);
}

.plugin-card__foot-start {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.plugin-card__menu-wrap {
  position: relative;
  flex: none;
  z-index: 2;
}

.plugin-card__menu-btn {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-tertiary);
  cursor: pointer;
  transition:
    color 140ms ease,
    background-color 140ms ease,
    border-color 140ms ease;
}

.plugin-card__menu-btn:hover,
.plugin-card__menu-btn.is-open {
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
  border-color: var(--panel-border);
}

.plugin-card__menu-btn:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}

/* MoviePilot 风格：Teleport 到 body；实色底，不被停用态拖虚 */
.plugin-card__menu {
  position: fixed;
  z-index: 90;
  min-width: 176px;
  padding: 6px;
  border-radius: 10px;
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  color: var(--color-text-primary);
  opacity: 1;
  filter: none;
  box-shadow:
    0 1px 0 color-mix(in srgb, #fff 55%, transparent) inset,
    0 8px 24px rgb(0 0 0 / 14%),
    0 2px 6px rgb(0 0 0 / 8%);
  transform-origin: top right;
  animation: plugin-menu-in 0.16s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes plugin-menu-in {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .plugin-card,
  .plugin-card__icon,
  .plugin-card__menu {
    transition: none;
    animation: none;
  }

  .plugin-card:hover,
  .plugin-card:hover .plugin-card__icon {
    transform: none;
  }
}

.plugin-card__menu button {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 36px;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  cursor: pointer;
  transition: background-color 0.12s ease;
}

.plugin-card__menu button:hover:not(:disabled) {
  background: var(--color-surface-secondary);
}

.plugin-card__menu button:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.plugin-card__menu button :deep(.icon) {
  color: var(--color-text-tertiary);
  flex: none;
}

.plugin-card__menu button.is-accent {
  color: var(--color-primary);
}

.plugin-card__menu button.is-accent :deep(.icon) {
  color: var(--color-primary);
}

.plugin-card__menu button.is-warn {
  color: var(--color-warning, #d97706);
}

.plugin-card__menu button.is-warn :deep(.icon) {
  color: var(--color-warning, #d97706);
}

.plugin-card__menu button.is-danger {
  color: var(--color-danger);
}

.plugin-card__menu button.is-danger :deep(.icon) {
  color: var(--color-danger);
}

.plugin-settings {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

.plugin-settings__identity {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  padding: 12px 14px;
  border-radius: var(--radius-lg);
  border: 1px solid color-mix(in srgb, hsl(var(--plugin-accent)) 18%, var(--panel-border));
  background:
    linear-gradient(
      135deg,
      color-mix(in srgb, hsl(var(--plugin-accent)) 12%, transparent) 0%,
      transparent 62%
    ),
    var(--color-surface-secondary);
}

.plugin-settings__mark {
  flex: none;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  padding: 8px;
  box-sizing: border-box;
  border-radius: 11px;
  background: #fff;
  box-shadow: 0 2px 8px rgb(0 0 0 / 12%);
  color: #1a1a1a;
}

.plugin-settings__mark-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.plugin-settings__identity-text {
  min-width: 0;
  flex: 1;
}

.plugin-settings__identity-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.plugin-settings__identity-name {
  min-width: 0;
  font-size: 15px;
  font-weight: 650;
  letter-spacing: -0.01em;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plugin-settings__identity-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.plugin-settings__loading {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
}

.plugin-settings__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
}

.plugin-settings__panel-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.plugin-settings__panel-icon {
  flex: none;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  color: hsl(var(--plugin-accent));
  background: color-mix(in srgb, hsl(var(--plugin-accent)) 14%, transparent);
}

.plugin-settings__panel-copy {
  min-width: 0;
  flex: 1;
}

.plugin-settings__panel-title {
  margin: 0;
  font-size: 13px;
  font-weight: 650;
  color: var(--color-text-primary);
}

.plugin-settings__panel-desc {
  margin: 3px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-text-tertiary);
}

.plugin-settings__field {
  display: block;
}

.plugin-settings__input {
  width: 100%;
  min-height: 42px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 13px;
  letter-spacing: 0.02em;
  outline: none;
  transition:
    border-color 160ms ease,
    box-shadow 160ms ease,
    background 160ms ease;
}

.plugin-settings__input::placeholder {
  color: var(--color-text-tertiary);
  letter-spacing: 0;
  font-family: inherit;
}

.plugin-settings__input:hover {
  border-color: color-mix(in srgb, hsl(var(--plugin-accent)) 28%, var(--panel-border));
}

.plugin-settings__input:focus {
  border-color: color-mix(in srgb, hsl(var(--plugin-accent)) 55%, var(--panel-border));
  background: var(--color-surface);
  box-shadow: 0 0 0 3px color-mix(in srgb, hsl(var(--plugin-accent)) 18%, transparent);
}

.plugin-settings__link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  font-size: 12px;
  font-weight: 550;
  color: hsl(var(--plugin-accent));
  text-decoration: none;
}

.plugin-settings__link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.plugin-settings__empty {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 72px;
  padding: 16px 18px;
  border-radius: var(--radius-lg);
  border: 1px dashed var(--panel-border);
  color: var(--color-text-tertiary);
  background: var(--color-surface-secondary);
}

.plugin-settings__empty p {
  margin: 0;
  font-size: 13px;
}

.plugin-settings__error {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-danger);
}

.plugin-settings .config__footer {
  width: 100%;
  justify-content: flex-end;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.poster-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space2);
}

.poster-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
}

.poster-card__cover {
  position: relative;
  aspect-ratio: 1;
  padding: 14px;
  background:
    linear-gradient(
      145deg,
      color-mix(in srgb, var(--color-surface) 50%, var(--color-surface-secondary)),
      var(--color-surface-secondary)
    );
  overflow: hidden;
}

.poster-card__img {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  display: block;
}

.poster-card__fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: color-mix(in srgb, var(--color-primary) 70%, var(--color-text-tertiary));
}

.poster-card__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px 10px;
}

.poster-card__head {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.poster-card__title {
  margin: 0;
  min-width: 0;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.poster-card__desc {
  margin: 0;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-text-secondary);
  min-height: 2.8em;
}

.poster-card__meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.poster-card__install {
  align-self: flex-start;
  margin-top: 2px;
}

.config {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

.config__panel {
  padding: 12px 14px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
}

.field__textarea {
  min-height: 112px;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: var(--font-caption-size);
}

.field__textarea--market {
  line-height: 1.55;
  border-radius: var(--radius-md);
}

.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
}

.switch-row__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.switch-row__label {
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.switch-row__hint {
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-text-tertiary);
}

.config__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  width: 100%;
}

.config__footer-right {
  display: flex;
  gap: var(--space2);
}

.tabular {
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1100px) {
  .poster-grid,
  .plugins__skel--poster,
  .plugin-grid,
  .plugins__skel {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .plugin-grid,
  .plugins__skel {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .poster-grid,
  .plugins__skel--poster {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .plugin-grid,
  .plugins__skel,
  .poster-grid,
  .plugins__skel--poster {
    grid-template-columns: 1fr;
  }

  .plugins__toolbar {
    flex-wrap: wrap;
  }
}
</style>
