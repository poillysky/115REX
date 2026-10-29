// 轻量操作反馈（docs/02 §10 AppToast）：只做「已发生的事」的旁路提示，不阻断操作、不承载确认。
// 需要用户决策的一律走 AppDialog，两者不混用。

import { defineStore } from 'pinia'
import { ref } from 'vue'

export type NoticeTone = 'info' | 'success' | 'warning' | 'danger'

export interface Notice {
  id: number
  tone: NoticeTone
  message: string
  /** 可选的下一步动作，例如失败后的「重试」；必须真的可执行 */
  action?: { label: string; run: () => void }
}

/** 同时最多堆 3 条，超出时挤掉最早的一条，避免遮住内容 */
const MAX_VISIBLE = 3

let seq = 0

export const useNotifyStore = defineStore('notify', () => {
  const items = ref<Notice[]>([])
  const timers = new Map<number, number>()

  function dismiss(id: number): void {
    const timer = timers.get(id)
    if (timer) {
      window.clearTimeout(timer)
      timers.delete(id)
    }
    items.value = items.value.filter((item) => item.id !== id)
  }

  function notify(
    message: string,
    options: { tone?: NoticeTone; action?: Notice['action']; duration?: number } = {},
  ): number {
    const tone = options.tone ?? 'info'
    const id = (seq += 1)
    items.value = [...items.value, { id, tone, message, action: options.action }].slice(-MAX_VISIBLE)

    // 危险的失败信息留久一点，其余按 micro 量级的 4 倍收走
    const duration = options.duration ?? (tone === 'danger' ? 6000 : 4000)
    timers.set(id, window.setTimeout(() => dismiss(id), duration))
    return id
  }

  const success = (message: string) => notify(message, { tone: 'success' })
  const failure = (message: string, retry?: () => void) =>
    notify(message, { tone: 'danger', action: retry ? { label: '重试', run: retry } : undefined })

  function clear(): void {
    timers.forEach((timer) => window.clearTimeout(timer))
    timers.clear()
    items.value = []
  }

  return { items, notify, success, failure, dismiss, clear }
})
