// API 错误。后端统一信封 { code, message, retryAfter }（docs/07 §3）。
// 客户端按 code 决定下一步，不把 code 直接抛给用户。

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly retryAfter?: number

  constructor(status: number, code: string, message: string, retryAfter?: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryAfter = retryAfter
  }

  get isAuthError(): boolean {
    return ['TOKEN_MISSING', 'TOKEN_EXPIRED', 'REFRESH_EXPIRED'].includes(this.code)
  }

  /** 可重试：上游抖动或适配器未就绪，文案要与网络错误区分。 */
  get isRetryable(): boolean {
    return ['UPSTREAM_ERROR', 'PROVIDER_NOT_READY', 'PROVIDER_UNAVAILABLE', 'PLAY_ADAPTER_NOT_READY'].includes(
      this.code,
    )
  }
}

function asApiError(error: unknown): ApiError | null {
  if (error instanceof ApiError) return error
  // HMR 可能复制出第二份 ApiError 类，instanceof 会失效；按形态兜底
  if (
    error &&
    typeof error === 'object' &&
    'code' in error &&
    'status' in error &&
    typeof (error as { message?: unknown }).message === 'string'
  ) {
    const item = error as { status: number; code: string; message: string; retryAfter?: number }
    return new ApiError(item.status, item.code, item.message, item.retryAfter)
  }
  return null
}

/** 面向用户的文案：说明原因 + 下一步，不暴露错误码。 */
export function describeError(error: unknown): string {
  const apiError = asApiError(error)
  if (apiError) {
    if (apiError.code === 'STORAGE_AUTH_REQUIRED') return '网盘授权已失效，请去设置页重新绑定'
    if (apiError.code === 'PLAY_ADAPTER_NOT_READY') return '播放服务暂未就绪，稍后重试'
    if (apiError.code === 'PLAY_INFO_RATE_LIMITED') return `刷新太频繁，请 ${apiError.retryAfter ?? 30} 秒后再试`
    if (apiError.code === 'INVALID_TARGET_DIR') return '目标目录不存在，请重新选择'
    if (apiError.code === 'QBITTORRENT_NOT_READY')
      return 'MoviePilot 还没配置好，请到「设定 → 系统设定」启用并填写地址与令牌'
    if (apiError.code === 'USERNAME_TAKEN') return '该用户名已被占用，换一个'
    if (apiError.code === 'REGISTRATION_CLOSED') return '账号已创建，请改用登录'
    if (apiError.code === 'INVALID_CREDENTIALS') return '账号或密码不正确'
    // PROVIDER_NOT_READY 后端已给可操作文案（如「请填写 TMDB API Key」），不要盖成笼统重试
    if (apiError.code === 'PROVIDER_NOT_READY') {
      return apiError.message || '相关服务尚未配置完成，请先到设定或插件管理检查'
    }
    if (apiError.code === 'UPSTREAM_ERROR' || apiError.code === 'PROVIDER_UNAVAILABLE') {
      return apiError.message || '资源源暂时不可用，请稍后重试'
    }
    if (apiError.isRetryable) return apiError.message || '暂时不可用，请稍后重试'
    return apiError.message
  }
  return '网络异常，请检查连接后重试'
}
