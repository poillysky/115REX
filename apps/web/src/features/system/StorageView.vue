<script setup lang="ts">
// 网盘绑定页（原「设置 · 网盘绑定」）。转存与播放都依赖 115 授权。
// 扫码是独立的模态任务：打开、扫码、确认、成功都在对话框内完成，卡片只负责展示授权状态。
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppErrorState from '@/features/shell/components/AppErrorState.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppQrcode from '@/features/shell/components/AppQrcode.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import SettingsPanel from '@/features/shell/components/SettingsPanel.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'
import { bindingStatusText, formatBytes, formatDate, formatRelative } from '@/domain/format'
import { describeError } from '@/core/api/error'
import { storageApi } from '@/data/api'
import type { BindingStatus, StorageAuthStart, StorageBinding } from '@/domain/contract'

type AuthPhase = 'requesting' | 'pending' | 'success' | 'expired' | 'failed'
type FlashTone = 'success' | 'neutral'

// 品牌标取自「离歌图标库」的方形 115（1），已下载到 public 下，不依赖外网
const PROVIDER_LOGO = '/providers/115.png'

const bindings = ref<StorageBinding[]>([])
const loading = ref(true)
const errorText = ref('')

// 扫码对话框：一次只存在一个会话，关闭即作废
const authOpen = ref(false)
const authMode = ref<'bind' | 'reauth'>('bind')
const authPhase = ref<AuthPhase>('requesting')
const authMessage = ref('')
const authError = ref('')
const authScanned = ref(false)
const authBusy = ref(false)
const session = ref<StorageAuthStart | null>(null)
const sessionExpiresAt = ref(0)
const clock = ref(Date.now())

// 解绑确认
const unbindOpen = ref(false)
const unbindBusy = ref(false)
const unbindError = ref('')

// 操作完成后的轻提示
const flash = ref<{ tone: FlashTone; text: string } | null>(null)

let pollTimer: ReturnType<typeof setTimeout> | null = null
let countdownTimer: ReturnType<typeof setInterval> | null = null
let flashTimer: ReturnType<typeof setTimeout> | null = null
let authRequestSeq = 0
let pollFailures = 0
let disposed = false

const fallbackBinding: StorageBinding = {
  provider: '115',
  status: 'unbound',
  displayName: null,
  avatarUrl: null,
  vipLevel: null,
  vipExpire: null,
  updatedAt: 0,
  syncedAt: null,
  quota: null,
}

const current = computed<StorageBinding>(() => bindings.value[0] ?? fallbackBinding)
const status = computed<BindingStatus>(() => current.value.status)
const connected = computed(() => status.value !== 'unbound')
const bindingTone = (value: BindingStatus) =>
  value === 'healthy' ? 'success' : value === 'unbound' ? 'neutral' : 'warning'

const accountName = computed(() => {
  const name = current.value.displayName
  return name && name !== '115 账号' ? name : '115 网盘'
})

const avatarUrl = computed(() => (connected.value ? current.value.avatarUrl || '' : ''))
const avatarBroken = ref(false)
watch(avatarUrl, () => {
  avatarBroken.value = false
})

const vipLabel = computed(() => {
  if (!connected.value) return ''
  return (current.value.vipLevel || '').trim()
})

const vipExpireText = computed(() => {
  const expire = current.value.vipExpire
  if (!expire) return ''
  return formatDate(expire)
})

const syncedText = computed(() => {
  if (!connected.value || !current.value.syncedAt) return ''
  return formatRelative(current.value.syncedAt)
})

/** 容量：115 没返回总量时整块隐藏，不显示 0 B 的假数据 */
const quota = computed(() => {
  const value = current.value.quota
  if (!connected.value || !value || value.totalBytes <= 0) return null
  const used = Math.min(Math.max(value.usedBytes, 0), value.totalBytes)
  return {
    usedText: formatBytes(used),
    totalText: formatBytes(value.totalBytes),
    freeText: formatBytes(value.totalBytes - used),
    percent: Math.round((used / value.totalBytes) * 100),
  }
})

const statusNotice = computed(() => {
  if (status.value === 'expiring') {
    return {
      tone: 'warning' as const,
      text: '访问令牌已到期，服务端正在自动续期，稍后会自动重试，无需重新扫码。',
    }
  }
  if (status.value === 'expired') {
    return {
      tone: 'danger' as const,
      text: '授权已失效，播放与转存不可用，请重新授权。',
    }
  }
  return null
})

const authTitle = computed(() =>
  authMode.value === 'bind' ? '绑定 115 账号' : '重新授权 115 账号',
)

const authDescription = computed(() => {
  if (authPhase.value === 'success' || authPhase.value === 'expired' || authPhase.value === 'failed') {
    return ''
  }
  return '打开 115 手机客户端，用「扫一扫」扫描二维码并确认登录。'
})

const authResultTitle = computed(() => {
  if (authPhase.value === 'success') return '绑定成功'
  if (authPhase.value === 'expired') return '二维码已过期'
  return '扫码未完成'
})

const authResultText = computed(() => {
  if (authPhase.value === 'success') {
    return '现在可以播放与转存 115 内容，授权令牌只保存在服务端。'
  }
  if (authPhase.value === 'expired') {
    return '二维码有效期 5 分钟，重新生成后即可继续。'
  }
  return authError.value || '重新生成二维码后再试一次。'
})

const isAuthResult = computed(
  () =>
    authPhase.value === 'success' ||
    authPhase.value === 'expired' ||
    authPhase.value === 'failed',
)

const remainingSeconds = computed(() =>
  Math.max(0, Math.ceil((sessionExpiresAt.value - clock.value) / 1000)),
)

const countdownText = computed(() => {
  const total = remainingSeconds.value
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

const authActionLabel = computed(() => {
  if (authPhase.value === 'requesting') return '生成中…'
  return authPhase.value === 'pending' ? '重新生成' : '重新生成二维码'
})

async function load(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const response = await storageApi.bindings()
    bindings.value = response.bindings
  } catch (error) {
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

function showFlash(tone: FlashTone, text: string): void {
  flash.value = { tone, text }
  if (flashTimer !== null) clearTimeout(flashTimer)
  flashTimer = setTimeout(() => {
    flash.value = null
    flashTimer = null
  }, 6000)
}

function stopPolling(): void {
  if (pollTimer !== null) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

function stopCountdown(): void {
  if (countdownTimer !== null) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

function schedulePoll(delaySeconds = 1): void {
  stopPolling()
  if (disposed || !session.value) return
  pollTimer = setTimeout(() => void pollOnce(), delaySeconds * 1000)
}

function startCountdown(): void {
  stopCountdown()
  countdownTimer = setInterval(() => {
    clock.value = Date.now()
    if (
      authPhase.value === 'pending' &&
      sessionExpiresAt.value > 0 &&
      clock.value >= sessionExpiresAt.value
    ) {
      stopPolling()
      stopCountdown()
      session.value = null
      authPhase.value = 'expired'
      authMessage.value = ''
      authError.value = '二维码已过期，请重新生成。'
    }
  }, 1000)
}

function openAuth(): void {
  authMode.value = connected.value ? 'reauth' : 'bind'
  authOpen.value = true
  void startAuth()
}

async function startAuth(): Promise<void> {
  const requestId = ++authRequestSeq
  authBusy.value = true
  authError.value = ''
  authMessage.value = '正在向 115 申请二维码…'
  authScanned.value = false
  authPhase.value = 'requesting'
  session.value = null
  sessionExpiresAt.value = 0
  pollFailures = 0
  stopPolling()
  stopCountdown()

  try {
    const started = await storageApi.startAuth()
    if (disposed || requestId !== authRequestSeq) return
    session.value = started
    sessionExpiresAt.value = Date.now() + started.expiresIn * 1000
    clock.value = Date.now()
    authPhase.value = 'pending'
    authMessage.value = '等待在 115 手机客户端扫码确认。'
    startCountdown()
    schedulePoll(Math.min(1, started.intervalSeconds))
  } catch (error) {
    if (disposed || requestId !== authRequestSeq) return
    authPhase.value = 'failed'
    authMessage.value = ''
    authError.value = describeError(error)
  } finally {
    if (requestId === authRequestSeq) authBusy.value = false
  }
}

async function pollOnce(): Promise<void> {
  const currentSession = session.value
  if (!currentSession || disposed || authPhase.value !== 'pending') return

  const sessionId = currentSession.sessionId
  try {
    const result = await storageApi.pollAuth(sessionId)
    if (disposed || session.value?.sessionId !== sessionId) return

    pollFailures = 0
    authMessage.value = result.message
    authScanned.value = result.message.includes('已扫码')

    if (result.state === 'authorized') {
      stopPolling()
      stopCountdown()
      session.value = null
      authPhase.value = 'success'
      authMessage.value = result.message || '115 绑定成功。'
      if (result.binding) bindings.value = [result.binding]
      showFlash('success', '115 账号已绑定，播放与转存已恢复。')
      return
    }

    if (result.state === 'expired' || result.state === 'failed') {
      stopPolling()
      stopCountdown()
      session.value = null
      authPhase.value = result.state
      authMessage.value = ''
      authError.value =
        result.message ||
        (result.state === 'expired' ? '二维码已过期，请重新生成。' : '扫码确认失败，请重试。')
      return
    }

    schedulePoll(result.retryAfter ?? currentSession.intervalSeconds)
  } catch (error) {
    if (disposed || session.value?.sessionId !== sessionId) return
    // 网络抖动不立刻终止会话，连续失败三次才收起二维码
    pollFailures += 1
    if (pollFailures < 3) {
      authMessage.value = '网络波动，正在重试…'
      schedulePoll(currentSession.intervalSeconds)
      return
    }
    stopPolling()
    stopCountdown()
    session.value = null
    authPhase.value = 'failed'
    authMessage.value = ''
    authError.value = describeError(error)
  }
}

function closeAuth(): void {
  // 让还在路上的 startAuth 结果失效，避免关掉后又自己打开
  authRequestSeq += 1
  authBusy.value = false
  pollFailures = 0
  stopPolling()
  stopCountdown()
  authOpen.value = false
  session.value = null
  sessionExpiresAt.value = 0
  authMessage.value = ''
  authError.value = ''
  authScanned.value = false
}

function onAuthOpenChange(open: boolean): void {
  if (!open) closeAuth()
}

async function confirmUnbind(): Promise<void> {
  unbindBusy.value = true
  unbindError.value = ''
  try {
    const response = await storageApi.unbind()
    bindings.value = response.bindings
    unbindOpen.value = false
    closeAuth()
    showFlash('neutral', '已解绑 115 账号，可随时重新扫码绑定。')
  } catch (error) {
    unbindError.value = describeError(error)
  } finally {
    unbindBusy.value = false
  }
}

function openUnbind(): void {
  unbindError.value = ''
  unbindOpen.value = true
}

function onUnbindOpenChange(open: boolean): void {
  if (!open) unbindError.value = ''
}

onMounted(() => void load())
onBeforeUnmount(() => {
  disposed = true
  stopPolling()
  stopCountdown()
  if (flashTimer !== null) clearTimeout(flashTimer)
})
</script>

<template>
  <SysStyles>
    <SettingsPanel>
      <AppErrorState v-if="errorText" :message="errorText" @retry="load" />

      <section v-else class="group">
        <div class="group__head">
          <h2 class="group__title">115 账号</h2>
        </div>

        <div class="group__body">
          <div v-if="loading" class="account account--loading">
            <AppSkeleton height="44px" width="44px" radius="var(--radius-md)" />
            <div class="account__main">
              <AppSkeleton height="15px" width="128px" />
              <AppSkeleton height="13px" width="220px" />
            </div>
          </div>

          <div v-else class="account">
            <span
              class="account__icon"
              :class="{
                'account__icon--on': connected,
                'account__icon--avatar': Boolean(avatarUrl) && !avatarBroken,
              }"
            >
              <img
                v-if="avatarUrl && !avatarBroken"
                class="account__avatar"
                :src="avatarUrl"
                alt=""
                width="44"
                height="44"
                referrerpolicy="no-referrer"
                @error="avatarBroken = true"
              />
              <img
                v-else
                class="account__logo"
                :src="PROVIDER_LOGO"
                alt=""
                width="36"
                height="36"
              />
            </span>

            <div class="account__main">
              <div class="account__title">
                <span class="account__name">{{ accountName }}</span>
                <AppBadge :tone="bindingTone(status)">{{ bindingStatusText(status) }}</AppBadge>
                <AppBadge v-if="vipLabel" tone="primary">{{ vipLabel }}</AppBadge>
              </div>
              <p v-if="connected && (vipExpireText || syncedText)" class="account__meta">
                <span v-if="vipExpireText">会员至 {{ vipExpireText }}</span>
                <span v-if="vipExpireText && syncedText" class="account__meta-sep" aria-hidden="true">·</span>
                <span v-if="syncedText">同步于 {{ syncedText }}</span>
              </p>
            </div>

            <div class="account__actions">
              <AppButton
                size="sm"
                :variant="connected && status === 'healthy' ? 'secondary' : 'primary'"
                @click="openAuth"
              >
                <AppIcon v-if="connected" name="refresh" :size="15" />
                {{ connected ? '重新授权' : '扫码绑定' }}
              </AppButton>
              <AppButton v-if="connected" variant="ghost" size="sm" @click="openUnbind">
                解绑
              </AppButton>
            </div>
          </div>

          <!-- 已授权才有账号概况：容量与占用 -->
          <div v-if="quota" class="quota">
            <div class="quota__head">
              <span class="quota__label">存储空间</span>
              <span class="quota__figure tabular">
                <strong>{{ quota.usedText }}</strong>
                <span class="quota__muted"> / {{ quota.totalText }}</span>
              </span>
            </div>

            <div
              class="quota__track"
              role="progressbar"
              aria-label="115 存储空间占用"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="quota.percent"
            >
              <span class="quota__fill" :style="{ width: `${quota.percent}%` }" />
            </div>

            <p class="quota__foot">
              <span class="quota__muted">剩余 {{ quota.freeText }}</span>
              <span class="quota__muted tabular">已用 {{ quota.percent }}%</span>
            </p>
          </div>

          <p v-if="flash" class="account__notice" :class="`account__notice--${flash.tone}`" role="status">
            <AppIcon :name="flash.tone === 'success' ? 'check' : 'alert'" :size="16" />
            {{ flash.text }}
          </p>

          <p
            v-else-if="statusNotice"
            class="account__notice"
            :class="`account__notice--${statusNotice.tone}`"
            role="status"
          >
            <AppIcon name="alert" :size="16" />
            {{ statusNotice.text }}
          </p>
        </div>
      </section>

      <!-- 扫码授权：二维码、轮询状态、成功/过期结果都在同一个对话框里 -->
      <AppDialog
        :open="authOpen"
        :title="authTitle"
        :description="authDescription"
        @update:open="onAuthOpenChange"
      >
        <!-- 常驻的读屏播报区：结果态替换内容时仍能读出来 -->
        <p class="visually-hidden" role="status" aria-live="polite">
          {{ isAuthResult ? `${authResultTitle}。${authResultText}` : '' }}
        </p>

        <div class="auth" :class="{ 'auth--result': isAuthResult }">
          <div v-if="isAuthResult" class="auth__result">
            <span
              class="auth__result-icon"
              :class="{ 'auth__result-icon--error': authPhase !== 'success' }"
            >
              <AppIcon :name="authPhase === 'success' ? 'check' : 'alert'" :size="28" />
            </span>
            <p class="auth__result-title">{{ authResultTitle }}</p>
            <p class="auth__result-desc">{{ authResultText }}</p>
          </div>

          <template v-else>
            <div class="auth__stage">
              <AppQrcode
                v-if="session"
                :value="session.qrcode"
                :size="192"
                label="115 登录二维码"
              />
              <span v-else class="auth__placeholder" aria-hidden="true">
                <span class="auth__spinner" />
              </span>
              <p v-if="session" class="auth__countdown tabular">
                二维码剩余 {{ countdownText }}
              </p>
              <p v-else class="auth__countdown">正在生成二维码…</p>
            </div>

            <div class="auth__side">
              <div class="auth__live" role="status" aria-live="polite">
                <span
                  class="auth__dot"
                  :class="{
                    'auth__dot--active': authPhase === 'pending',
                    'auth__dot--scanned': authScanned,
                  }"
                />
                <p class="auth__message">{{ authError || authMessage }}</p>
              </div>

              <ol class="auth__steps">
                <li><span class="auth__step">1</span>打开 115 手机客户端</li>
                <li><span class="auth__step">2</span>点右上角「扫一扫」</li>
                <li><span class="auth__step">3</span>确认登录，等待自动完成</li>
              </ol>

              <p class="auth__fineprint">二维码 5 分钟内有效；令牌只保存在服务端。</p>
            </div>
          </template>
        </div>

        <template #footer>
          <template v-if="authPhase === 'success'">
            <AppButton size="sm" variant="primary" @click="closeAuth">完成</AppButton>
          </template>
          <template v-else-if="authPhase === 'pending' || authPhase === 'requesting'">
            <AppButton size="sm" variant="ghost" @click="closeAuth">取消</AppButton>
            <AppButton
              size="sm"
              :loading="authBusy"
              :disabled="authPhase === 'requesting'"
              @click="startAuth"
            >
              {{ authActionLabel }}
            </AppButton>
          </template>
          <template v-else>
            <AppButton size="sm" variant="ghost" @click="closeAuth">关闭</AppButton>
            <AppButton size="sm" variant="primary" :loading="authBusy" @click="startAuth">
              重新生成二维码
            </AppButton>
          </template>
        </template>
      </AppDialog>

      <!-- 解绑属于不可逆操作，必须二次确认（docs/02 §11 设置页） -->
      <AppDialog
        v-model:open="unbindOpen"
        size="sm"
        title="解绑 115 账号？"
        description="解绑会清除服务端保存的授权令牌，正在播放或转存的 115 内容会中断；影视库与已有文件不受影响。"
        @update:open="onUnbindOpenChange"
      >
        <div class="unbind">
          <span class="unbind__icon" aria-hidden="true">
            <AppIcon name="alert" :size="20" />
          </span>
          <p class="unbind__text">解绑后可随时重新扫码绑定，令牌不会留在浏览器里。</p>
        </div>
        <p v-if="unbindError" class="unbind__error" role="alert">{{ unbindError }}</p>

        <template #footer>
          <AppButton size="sm" variant="ghost" @click="unbindOpen = false">取消</AppButton>
          <AppButton size="sm" variant="danger" :loading="unbindBusy" @click="confirmUnbind">
            确认解绑
          </AppButton>
        </template>
      </AppDialog>
    </SettingsPanel>
  </SysStyles>
</template>

<style scoped>
/* ---- 账号卡片 ---- */
.account {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space4) var(--space5);
}

.account + .account,
.account__notice {
  border-top: 1px solid var(--color-separator);
}

.account--loading {
  align-items: flex-start;
}

.account--loading .account__main {
  gap: var(--space2);
  padding-top: var(--space1);
}

.account__icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
}

/* 已连接后品牌标本身足够辨识，底板完全透明，不再加描边或色块 */
.account__icon--on {
  background: transparent;
  box-shadow: none;
}

.account__icon--avatar {
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
}

.account__logo {
  display: block;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  object-fit: contain;
}

.account__avatar {
  display: block;
  width: 44px;
  height: 44px;
  object-fit: cover;
}

/* 远程图标加载失败时退回中性底板，不显示破图 */
.account__logo:not([src]),
.account__logo[src=''] {
  visibility: hidden;
}

.account__main {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.account__title {
  display: flex;
  align-items: center;
  gap: var(--space2);
  flex-wrap: wrap;
}

.account__name {
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.account__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space1);
  margin: 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.account__meta-sep {
  opacity: 0.7;
}

.account__actions {
  display: flex;
  align-items: center;
  gap: var(--space2);
  flex-wrap: wrap;
  margin-left: auto;
}

/* 轻提示 / 状态提示：同一行语言，只差语义色 */
.account__notice {
  display: flex;
  align-items: flex-start;
  gap: var(--space2);
  max-width: none;
  padding: var(--space3) var(--space5);
  font-size: var(--font-caption-size);
  line-height: 1.6;
}

.account__notice .icon {
  margin-top: 3px;
}

.account__notice--success {
  background: color-mix(in srgb, var(--color-success) 8%, transparent);
  color: var(--color-success);
}

.account__notice--warning {
  background: color-mix(in srgb, var(--color-warning) 8%, transparent);
  color: var(--color-warning);
}

.account__notice--danger {
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
  color: var(--color-danger);
}

.account__notice--neutral {
  color: var(--color-text-secondary);
}

/* ---- 容量 ---- */
.quota {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  padding: var(--space4) var(--space5);
  border-top: 1px solid var(--color-separator);
}

.quota__head,
.quota__foot {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space3);
}

.quota__label {
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
}

.quota__figure {
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.quota__figure strong {
  font-weight: var(--font-label-weight);
}

.quota__muted {
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.quota__track {
  overflow: hidden;
  width: 100%;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
}

.quota__fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  transition: width var(--duration-page) ease;
}

/* ---- 扫码对话框 ---- */
.auth {
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr);
  gap: var(--space5);
  align-items: center;
}

.auth__stage {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space2);
  padding: var(--space3);
  border-radius: var(--radius-lg);
  background: var(--color-surface-secondary);
}

.auth__placeholder {
  display: grid;
  place-items: center;
  width: 192px;
  height: 192px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.auth__placeholder .auth__spinner {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  border: 2px solid var(--color-separator);
  border-top-color: var(--color-primary);
  animation: auth-spin calc(var(--duration-page) * 2.7) linear infinite;
}

.auth__countdown {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.auth__side {
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  min-width: 0;
}

.auth__live {
  display: flex;
  align-items: flex-start;
  gap: var(--space2);
}

.auth__dot {
  width: 6px;
  height: 6px;
  margin-top: 8px;
  flex: none;
  border-radius: var(--radius-full);
  background: var(--color-text-secondary);
}

.auth__dot--active {
  background: var(--color-primary);
  animation: auth-pulse calc(var(--duration-page) * 5.3) ease-in-out infinite;
}

.auth__dot--scanned {
  background: var(--color-success);
  animation: none;
}

.auth__message {
  font-size: var(--font-label-size);
  line-height: 1.5;
  color: var(--color-text-primary);
}

.auth__steps {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.auth__steps li {
  display: flex;
  align-items: center;
  gap: var(--space2);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.auth__step {
  display: grid;
  flex: none;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  color: var(--color-text-secondary);
  font-size: var(--font-caption-size);
}

.auth__fineprint {
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-tertiary);
}

/* 结果态：二维码退场，只留图标与结论 */
.auth--result {
  display: flex;
  justify-content: center;
  padding: var(--space4) 0;
}

.auth__result {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space2);
  max-width: 44ch;
  text-align: center;
  animation: auth-result-in var(--duration-page) ease both;
}

.auth__result-icon {
  display: grid;
  place-items: center;
  width: 56px;
  height: 56px;
  margin-bottom: var(--space1);
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

.auth__result-icon--error {
  background: color-mix(in srgb, var(--color-danger) 12%, transparent);
  color: var(--color-danger);
}

.auth__result-title {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  letter-spacing: var(--font-heading3-tracking);
  color: var(--color-text-primary);
}

.auth__result-desc {
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

/* ---- 解绑确认 ---- */
.unbind {
  display: flex;
  align-items: flex-start;
  gap: var(--space3);
  padding: var(--space3);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-danger) 8%, transparent);
}

.unbind__icon {
  display: grid;
  flex: none;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  color: var(--color-danger);
}

.unbind__text {
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.unbind__error {
  margin-top: var(--space3);
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-danger);
}

@keyframes auth-spin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes auth-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

@keyframes auth-result-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 640px) {
  .account {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .account__main {
    flex: 1 1 calc(100% - 44px - var(--space3));
  }

  .account__actions {
    width: 100%;
    margin-left: 0;
    padding-left: calc(44px + var(--space3));
  }

  .auth {
    grid-template-columns: 1fr;
    gap: var(--space4);
  }

  .auth__stage {
    width: fit-content;
    margin-inline: auto;
  }
}

@media (prefers-reduced-motion: reduce) {
  .auth__dot--active,
  .auth__placeholder .auth__spinner,
  .auth__result {
    animation: none;
  }
}
</style>
