// HTTP 客户端。两条硬规则：
// 1. 刷新令牌**必须单飞**（docs/08 §5 不变量 6），并发刷新会被服务端重放检测踢下线。
// 2. 业务错误按统一信封解析，抛 ApiError，调用方按 code 处理。

import { sessionStore, deviceId } from '@/core/session'
import { ApiError } from '@/core/api/error'

const BASE_URL = '/api/v1'

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

interface RequestOptions {
  method?: Method
  body?: unknown
  query?: Record<string, string | number | boolean | null | undefined>
  /** 内部使用：刷新后的重放，避免无限递归 */
  retried?: boolean
  /** 关闭鉴权重定向（登录接口用） */
  anonymous?: boolean
}

let refreshPromise: Promise<boolean> | null = null

/** 刷新失败时的回调由应用层注入，避免 core 依赖 router。 */
let onUnauthorized: () => void = () => {}
export function setUnauthorizedHandler(handler: () => void): void {
  onUnauthorized = handler
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = new URL(BASE_URL + path, window.location.origin)
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, String(value))
    }
  }
  return url.toString()
}

function headers(anonymous: boolean): Record<string, string> {
  const result: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Device-Id': deviceId(),
    'X-App-Version': 'web-0.1.0',
    'X-Client-Platform': 'web',
  }
  const access = sessionStore.access()
  if (!anonymous && access) result.Authorization = `Bearer ${access}`
  return result
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  const text = await response.text()
  const trimmed = text.trim()
  // SPA 回退或代理异常时会拿到 HTML；不能静默 JSON.parse 成「网络异常」
  if (trimmed.startsWith('<!') || trimmed.toLowerCase().startsWith('<html')) {
    throw new ApiError(
      response.status,
      'INTERNAL_ERROR',
      '接口返回了网页而不是数据，请确认后端已启动且路由已加载',
    )
  }
  let payload: unknown = null
  if (trimmed) {
    try {
      payload = JSON.parse(trimmed)
    } catch {
      throw new ApiError(response.status, 'INTERNAL_ERROR', '接口响应不是合法 JSON')
    }
  }
  if (!response.ok) {
    const envelope = payload as { code?: string; message?: string; retryAfter?: number } | null
    throw new ApiError(
      response.status,
      envelope?.code ?? 'INTERNAL_ERROR',
      envelope?.message ?? '请求失败',
      envelope?.retryAfter,
    )
  }
  return payload as T
}

async function refreshTokens(): Promise<boolean> {
  const refreshToken = sessionStore.refresh()
  if (!refreshToken) return false
  try {
    const response = await fetch(buildUrl('/auth/refresh'), {
      method: 'POST',
      headers: headers(true),
      body: JSON.stringify({ refreshToken }),
    })
    if (!response.ok) return false
    const pair = (await response.json()) as { accessToken: string; refreshToken: string }
    // 必须覆盖旧 refresh（滚动令牌）
    sessionStore.save(pair.accessToken, pair.refreshToken)
    return true
  } catch {
    return false
  }
}

/** 单飞刷新：多次并发调用共享同一个 Promise。 */
function refreshOnce(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = refreshTokens().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const anonymous = options.anonymous ?? false
  const response = await fetch(buildUrl(path, options.query), {
    method: options.method ?? 'GET',
    headers: headers(anonymous),
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    // API 绝不能吃浏览器对错误 HTML/旧响应的缓存（曾出现 offline 被缓存成 SPA 首页）
    cache: 'no-store',
  })

  if (response.status === 401 && !anonymous && !options.retried && sessionStore.refresh()) {
    const ok = await refreshOnce()
    if (ok) {
      return request<T>(path, { ...options, retried: true })
    }
    sessionStore.clear()
    onUnauthorized()
  }

  return parse<T>(response)
}

export const http = {
  get: <T>(path: string, query?: RequestOptions['query']) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown, query?: RequestOptions['query']) =>
    request<T>(path, { method: 'POST', body, query }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
