// 会话控制器：登录态、能力清单、失效跳转（docs/04 §5 的 Web 对应物）。

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { authApi } from '@/data/api'
import { sessionStore } from '@/core/session'
import type { Capabilities, MeResponse, User } from '@/domain/contract'

const DEFAULT_CAPABILITIES: Capabilities = {
  search: true,
  transfer: true,
  push: false,
  download: false,
  play: false,
  playbackAdapterReady: false,
}

export const useSessionStore = defineStore('session', () => {
  const user = ref<User | null>(null)
  const me = ref<MeResponse | null>(null)
  const loading = ref(false)
  /** 一个账号都没有时为 true：首次打开的 Web 走注册，而不是登录。 */
  const registrationOpen = ref(false)

  const isAuthenticated = computed(() => Boolean(sessionStore.access()))
  const capabilities = computed(() => me.value?.capabilities ?? DEFAULT_CAPABILITIES)
  const displayName = computed(() => user.value?.displayName ?? sessionStore.userName() ?? '')
  const mockMode = computed(() => me.value?.server.mockMode ?? false)
  const avatarUrl = computed(() => user.value?.avatarUrl ?? null)
  const initial = computed(() => (displayName.value || 'R').slice(0, 1).toUpperCase())

  async function checkRegistration(): Promise<void> {
    try {
      const status = await authApi.registrationStatus()
      registrationOpen.value = status.registrationOpen
    } catch {
      // 探测失败不拦登录入口
      registrationOpen.value = false
    }
  }

  async function register(username: string, password: string): Promise<void> {
    loading.value = true
    try {
      const response = await authApi.register(username, password)
      sessionStore.save(response.accessToken, response.refreshToken, response.user.displayName)
      user.value = response.user
      registrationOpen.value = false
      await loadMe()
    } finally {
      loading.value = false
    }
  }

  async function login(username: string, password: string): Promise<void> {
    loading.value = true
    try {
      const response = await authApi.login(username, password)
      sessionStore.save(response.accessToken, response.refreshToken, response.user.displayName)
      user.value = response.user
      await loadMe()
    } finally {
      loading.value = false
    }
  }

  async function loadMe(): Promise<void> {
    if (!isAuthenticated.value) return
    me.value = await authApi.me()
    user.value = me.value.user
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      /* 注销失败也要清本地 */
    }
    sessionStore.clear()
    user.value = null
    me.value = null
  }

  async function updateProfile(patch: {
    displayName?: string
    avatarUrl?: string
  }): Promise<void> {
    const updated = await authApi.updateProfile(patch)
    user.value = updated
    if (me.value) me.value = { ...me.value, user: updated }
    sessionStore.save(undefined, undefined, updated.displayName)
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await authApi.changePassword(currentPassword, newPassword)
    // 改密后服务端吊销全部 refresh，本地只能重新登录
    clear()
  }

  function clear(): void {
    sessionStore.clear()
    user.value = null
    me.value = null
  }

  return {
    user,
    me,
    loading,
    registrationOpen,
    isAuthenticated,
    capabilities,
    displayName,
    mockMode,
    avatarUrl,
    initial,
    checkRegistration,
    register,
    login,
    loadMe,
    updateProfile,
    changePassword,
    logout,
    clear,
  }
})
