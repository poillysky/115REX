// 路由表（docs/03 §3）。页面不自己造导航，导航形态由 AppShell 统一提供。
// 例外：播放页是全屏沉浸页，不套 AppShell。
//
// 导航只有一层：所有页面都是侧栏里直接点到的平级入口，不再有二级外壳页。

import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { sessionStore } from '@/core/session'

/** 占位页：功能未接入前先占住导航与地址 */
const PlaceholderView = () => import('@/features/shell/PlaceholderView.vue')

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'index',
    component: PlaceholderView,
    meta: { title: '仪表盘', width: 'wide' },
  },
  {
    path: '/discover/movie',
    name: 'discover-movie',
    component: () => import('@/features/discover/DiscoverMovieView.vue'),
    meta: { title: '影视', width: 'wide' },
  },
  {
    path: '/discover/drama',
    name: 'discover-drama',
    component: PlaceholderView,
    meta: { title: '短剧', width: 'wide' },
  },
  {
    path: '/discover/girl',
    name: 'discover-girl',
    component: PlaceholderView,
    meta: { title: '小姐姐', width: 'wide' },
  },
  {
    path: '/discover/meta/:source/:id',
    name: 'meta-detail',
    component: () => import('@/features/discover/MetaDetailView.vue'),
    meta: { title: '详情', width: 'wide' },
  },
  {
    path: '/library/:id',
    name: 'detail',
    component: () => import('@/features/detail/DetailView.vue'),
    meta: { title: '详情', width: 'wide' },
  },
  {
    path: '/play/:id',
    name: 'player',
    component: () => import('@/features/player/PlayerView.vue'),
    meta: { bare: true, title: '播放' },
  },
  {
    path: '/drive/files',
    name: 'drive-files',
    component: () => import('@/features/drive/DriveFilesView.vue'),
    meta: { title: '文件浏览', width: 'wide' },
  },
  {
    path: '/drive/cloud',
    name: 'drive-cloud',
    component: () => import('@/features/drive/CloudDownloadView.vue'),
    meta: { title: '云下载', width: 'wide' },
  },
  {
    path: '/flows/organize',
    name: 'flows-organize',
    component: () => import('@/features/flows/OrganizeView.vue'),
    meta: { title: '文件整理', width: 'wide' },
  },
  {
    path: '/flows/workflow',
    name: 'flows-workflow',
    component: PlaceholderView,
    meta: { title: '自动化工作流', width: 'wide' },
  },
  {
    path: '/system/115',
    name: 'system-115',
    component: () => import('@/features/system/StorageView.vue'),
    meta: { title: '网盘管理', width: 'wide' },
  },
  {
    path: '/system/plugins',
    name: 'system-plugins',
    component: () => import('@/features/system/PluginsView.vue'),
    meta: { title: '插件管理', width: 'wide' },
  },
  {
    path: '/system/settings',
    name: 'system-settings',
    component: () => import('@/features/system/SettingsView.vue'),
    meta: { title: '设定', width: 'wide' },
  },
  {
    path: '/account',
    name: 'account',
    component: () => import('@/features/account/AccountView.vue'),
    meta: { title: '账号管理', width: 'wide' },
  },
  {
    path: '/account/theme',
    name: 'account-theme',
    component: () => import('@/features/account/ThemeView.vue'),
    meta: { title: '主题管理', width: 'wide' },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/features/login/LoginView.vue'),
    meta: { title: '登录', public: true, bare: true },
  },
  // 已删除的入口与旧的二级地址一律回到仪表盘
  { path: '/search', redirect: { name: 'index' } },
  { path: '/discover', redirect: { name: 'discover-movie' } },
  { path: '/drive', redirect: { name: 'drive-files' } },
  { path: '/flows', redirect: { name: 'flows-organize' } },
  { path: '/flows/tasks', redirect: { name: 'index' } },
  { path: '/system', redirect: { name: 'system-115' } },
  { path: '/system/settings/network', redirect: { name: 'system-settings' } },
  { path: '/system/settings/danger', redirect: { name: 'system-settings' } },
  { path: '/:pathMatch(.*)*', redirect: { name: 'index' } },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach((to) => {
  if (to.meta.public) return true
  if (!sessionStore.access()) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} · 115REX` : '115REX'
})
