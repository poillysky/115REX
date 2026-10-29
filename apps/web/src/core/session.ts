// 会话与设备标识的本地存储。只存令牌与用户名，不存任何网盘凭据。

const ACCESS_KEY = 'rex.accessToken'
const REFRESH_KEY = 'rex.refreshToken'
const USER_KEY = 'rex.userName'
const DEVICE_KEY = 'rex.deviceId'

function readLocal(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeLocal(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* 隐私模式下忽略 */
  }
}

export const sessionStore = {
  access: () => readLocal(ACCESS_KEY),
  refresh: () => readLocal(REFRESH_KEY),
  userName: () => readLocal(USER_KEY),

  /** 只更新某项时传 undefined，已存的值不会被动。 */
  save(access?: string, refresh?: string, userName?: string): void {
    if (access) writeLocal(ACCESS_KEY, access)
    if (refresh) writeLocal(REFRESH_KEY, refresh)
    if (userName) writeLocal(USER_KEY, userName)
  },

  clear(): void {
    writeLocal(ACCESS_KEY, null)
    writeLocal(REFRESH_KEY, null)
    writeLocal(USER_KEY, null)
  },
}

/** 设备 ID：首次访问生成并持久化，随每个请求带上（docs/07 §1）。 */
export function deviceId(): string {
  let id = readLocal(DEVICE_KEY)
  if (!id) {
    id = `web-${crypto.randomUUID()}`
    writeLocal(DEVICE_KEY, id)
  }
  return id
}
