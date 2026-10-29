// 动作控制器：发起后就地轮询状态，不阻塞浏览（docs/03 §4、§7）。

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { actionApi } from '@/data/api'
import { describeError } from '@/core/api/error'
import type { ActionKind, ActionRecord, ActionStatus } from '@/domain/contract'
import { useNotifyStore } from '@/application/notify'

/** 动作用户语言表达：转存 / 推送 / 下载，提示文案与行内状态保持同一措辞 */
const KIND_LABEL: Record<ActionKind, string> = {
  transfer: '转存',
  push: '推送',
  download: '下载',
}

interface RowState {
  actionId: string | null
  status: ActionStatus | 'idle'
  failureReason: string | null
  itemId: string | null
}

const POLL_INTERVAL_MS = 1200
const POLL_MAX_ATTEMPTS = 20

export const useActionStore = defineStore('action', () => {
  const notify = useNotifyStore()
  // 以候选 ref 为键，行内更新，不打断当前浏览
  const rows = ref<Record<string, RowState>>({})
  const history = ref<ActionRecord[]>([])
  const targetDir = ref<string | null>(localStorage.getItem('rex.targetDir'))

  /** 仍在进行中的动作条数，供顶部通知角标使用。 */
  const activeCount = computed(
    () =>
      Object.values(rows.value).filter((row) => row.status === 'pending' || row.status === 'running')
        .length,
  )

  function rowOf(ref: string): RowState {
    if (!rows.value[ref]) {
      rows.value[ref] = { actionId: null, status: 'idle', failureReason: null, itemId: null }
    }
    return rows.value[ref]
  }

  function rememberDir(dir: string | null): void {
    targetDir.value = dir
    if (dir) localStorage.setItem('rex.targetDir', dir)
  }

  async function trigger(providerId: string, ref: string, kind: ActionKind): Promise<void> {
    const row = rowOf(ref)
    row.status = 'pending'
    row.failureReason = null
    try {
      // 下载走客户端（qBittorrent 等），没有网盘目录的概念；只有转存/推送才带目标目录
      const accepted = await actionApi.create(
        providerId,
        ref,
        kind,
        kind === 'download' ? null : targetDir.value,
      )
      row.actionId = accepted.actionId
      void poll(ref, accepted.actionId, kind)
    } catch (error) {
      row.status = 'failed'
      row.failureReason = describeError(error)
      notify.failure(`${KIND_LABEL[kind]}没能发起：${row.failureReason}`, () =>
        void trigger(providerId, ref, kind),
      )
    }
  }

  async function poll(ref: string, actionId: string, kind: ActionKind): Promise<void> {
    const row = rowOf(ref)
    for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
      try {
        const record = await actionApi.get(actionId)
        row.status = record.status
        row.failureReason = record.failureReason
        row.itemId = record.itemId
        if (record.status === 'succeeded') {
          notify.success(`${KIND_LABEL[kind]}已完成`)
          return
        }
        if (record.status === 'failed') {
          notify.notify(`${KIND_LABEL[kind]}失败：${record.failureReason ?? '服务端未给出原因'}`, {
            tone: 'warning',
          })
          return
        }
        if (record.status === 'cancelled') return
      } catch (error) {
        row.status = 'failed'
        row.failureReason = describeError(error)
        notify.failure(`${KIND_LABEL[kind]}状态读取失败：${row.failureReason}`)
        return
      }
    }
    notify.notify(`${KIND_LABEL[kind]}耗时较长，可稍后在动作记录里查看结果`, { tone: 'warning' })
  }

  async function loadHistory(): Promise<void> {
    const response = await actionApi.list()
    history.value = response.actions
  }

  async function cancel(ref: string): Promise<void> {
    const row = rowOf(ref)
    if (!row.actionId) return
    try {
      const record = await actionApi.cancel(row.actionId)
      row.status = record.status
      notify.notify(`${KIND_LABEL[record.kind]}已取消`)
    } catch (error) {
      row.failureReason = describeError(error)
      notify.failure(`取消失败：${row.failureReason}`)
    }
  }

  return { rows, history, targetDir, activeCount, rowOf, rememberDir, trigger, loadHistory, cancel }
})
