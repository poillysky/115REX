<script setup lang="ts">
// 播放页（docs/03 §5）：全屏、无导航；快捷键；
// 错误区分「适配器未就绪」「地址失效」「网盘授权失效」，各给下一步。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppSkeleton from '@/features/shell/components/AppSkeleton.vue'
import { formatDuration } from '@/domain/format'
import { ApiError, describeError } from '@/core/api/error'
import { libraryApi } from '@/data/api'
import { useLibraryStore } from '@/application/library'
import type { PlayInfo } from '@/domain/contract'

const route = useRoute()
const router = useRouter()
const library = useLibraryStore()

const videoEl = ref<HTMLVideoElement | null>(null)
const playInfo = ref<PlayInfo | null>(null)
const loading = ref(true)
const errorText = ref('')
const errorCode = ref('')
const controlsVisible = ref(true)

const playing = ref(false)
const muted = ref(false)
const current = ref(0)
const duration = ref(0)
const activeSubtitle = ref<string>('off')

let hideTimer: number | undefined

const id = computed(() => String(route.params.id))
const item = computed(() => (library.detail?.id === id.value ? library.detail : null))

/** 错误到下一步动作的映射（docs/03 §5）。 */
const nextStep = computed(() => {
  if (errorCode.value === 'PLAY_ADAPTER_NOT_READY') return '播放适配器未就绪，稍后重试'
  if (errorCode.value === 'PLAY_URL_EXPIRED') return '播放地址已失效，重新获取'
  if (errorCode.value === 'STORAGE_AUTH_REQUIRED') return '网盘授权已失效，去设置页重新绑定'
  return errorText.value
})

async function prepare(): Promise<void> {
  loading.value = true
  errorText.value = ''
  errorCode.value = ''
  try {
    if (!item.value) await library.loadDetail(id.value)
    playInfo.value = await libraryApi.playInfo(id.value)
    activeSubtitle.value = item.value?.subtitles[0]?.id ?? 'off'
  } catch (error) {
    errorCode.value = error instanceof ApiError ? error.code : ''
    errorText.value = describeError(error)
  } finally {
    loading.value = false
  }
}

function togglePlay(): void {
  const video = videoEl.value
  if (!video) return
  if (video.paused) void video.play()
  else video.pause()
}

function seek(delta: number): void {
  const video = videoEl.value
  if (!video) return
  video.currentTime = Math.min(Math.max(0, video.currentTime + delta), video.duration || 0)
}

function setVolume(delta: number): void {
  const video = videoEl.value
  if (!video) return
  video.volume = Math.min(1, Math.max(0, video.volume + delta))
  muted.value = video.muted
}

function toggleMute(): void {
  const video = videoEl.value
  if (!video) return
  video.muted = !video.muted
  muted.value = video.muted
}

async function toggleFullscreen(): Promise<void> {
  if (document.fullscreenElement) await document.exitFullscreen()
  else await document.documentElement.requestFullscreen()
}

function subtitleUrl(subtitleId: string): string {
  const token = playInfo.value?.playToken ?? ''
  return `/api/v1/assets/sub/${subtitleId}?playToken=${encodeURIComponent(token)}`
}

function onKeydown(event: KeyboardEvent): void {
  if (event.target instanceof HTMLSelectElement) return
  switch (event.key) {
    case ' ':
      event.preventDefault()
      togglePlay()
      break
    case 'ArrowLeft':
      seek(-10)
      break
    case 'ArrowRight':
      seek(10)
      break
    case 'ArrowUp':
      event.preventDefault()
      setVolume(0.1)
      break
    case 'ArrowDown':
      event.preventDefault()
      setVolume(-0.1)
      break
    case 'f':
    case 'F':
      void toggleFullscreen()
      break
    case 'Escape':
      if (document.fullscreenElement) return
      void router.back()
      break
    default:
      break
  }
  revealControls()
}

function revealControls(): void {
  controlsVisible.value = true
  window.clearTimeout(hideTimer)
  hideTimer = window.setTimeout(() => {
    if (playing.value) controlsVisible.value = false
  }, 2600)
}

function onTimeUpdate(): void {
  const video = videoEl.value
  if (!video) return
  current.value = video.currentTime
  duration.value = video.duration || 0
}

function onLoaded(): void {
  const video = videoEl.value
  if (!video) return
  const start = playInfo.value?.startPositionSeconds ?? 0
  if (start > 0 && start < (video.duration || Infinity) - 5) video.currentTime = start
  void video.play().catch(() => {
    /* 浏览器自动播放策略：让用户手动点播放 */
  })
}

// 离开播放页时回写进度（服务端取较新者，不会覆盖更新的位置）
async function reportProgress(): Promise<void> {
  const video = videoEl.value
  if (!video || !item.value) return
  const position = Math.floor(video.currentTime)
  if (position <= 0) return
  try {
    await libraryApi.putProgress(item.value.id, position)
  } catch {
    /* 进度回写失败不打扰观看 */
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  void prepare()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  window.clearTimeout(hideTimer)
  void reportProgress()
})
</script>

<template>
  <div class="player" @mousemove="revealControls">
    <div v-if="loading" class="player__loading">
      <AppSkeleton height="60vh" radius="var(--radius-lg)" />
      <AppSkeleton height="20px" width="240px" />
    </div>

    <div v-else-if="!playInfo" class="player__error" role="alert">
      <AppIcon name="alert" :size="28" />
      <p class="player__error-title">{{ nextStep }}</p>
      <div class="player__error-actions">
        <AppButton variant="primary" size="sm" @click="prepare">重试</AppButton>
        <AppButton
          v-if="errorCode === 'STORAGE_AUTH_REQUIRED'"
          size="sm"
          @click="router.push({ name: 'system-115' })"
        >
          去设置
        </AppButton>
        <AppButton size="sm" @click="router.back()">返回</AppButton>
      </div>
    </div>

    <template v-else>
      <video
        ref="videoEl"
        class="player__video"
        :src="playInfo.url"
        playsinline
        preload="metadata"
        @loadedmetadata="onLoaded"
        @timeupdate="onTimeUpdate"
        @play="playing = true"
        @pause="playing = false"
        @click="togglePlay"
      >
        <track
          v-for="track in playInfo.subtitles"
          :key="track.id"
          kind="subtitles"
          :src="subtitleUrl(track.id)"
          :label="track.label"
          :srclang="track.lang"
          :default="track.id === activeSubtitle"
        />
      </video>

      <!-- 控制层：玻璃只用于控制层（docs/02 §6.1） -->
      <div class="player__controls" :class="{ 'is-hidden': !controlsVisible }">
        <div class="player__top">
          <AppButton variant="ghost" size="sm" @click="router.back()">
            <AppIcon name="chevron-left" :size="18" />
            退出
          </AppButton>
          <span class="player__title">{{ item?.title ?? '播放' }}</span>
        </div>

        <div class="player__bar">
          <button type="button" class="player__btn" :aria-label="playing ? '暂停' : '播放'" @click="togglePlay">
            <AppIcon :name="playing ? 'pause' : 'play'" :size="20" />
          </button>
          <span class="player__time tabular">
            {{ formatDuration(current) }} / {{ formatDuration(duration || item?.durationSeconds || null) }}
          </span>
          <input
            class="player__seek"
            type="range"
            min="0"
            :max="duration || item?.durationSeconds || 0"
            step="1"
            :value="current"
            aria-label="播放进度"
            @input="(event) => {
              const video = videoEl
              if (video) video.currentTime = Number((event.target as HTMLInputElement).value)
            }"
          />
          <button type="button" class="player__btn" :aria-label="muted ? '取消静音' : '静音'" @click="toggleMute">
            <AppIcon :name="muted ? 'volume-muted' : 'volume'" :size="20" />
          </button>
          <select v-model="activeSubtitle" class="player__select" aria-label="字幕">
            <option value="off">字幕关</option>
            <option v-for="track in playInfo.subtitles" :key="track.id" :value="track.id">
              {{ track.label }}
            </option>
          </select>
          <button type="button" class="player__btn" aria-label="全屏" @click="toggleFullscreen">
            <AppIcon name="fullscreen" :size="20" />
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.player {
  position: relative;
  display: grid;
  place-items: center;
  width: 100vw;
  height: 100vh;
  background: #000;
  overflow: hidden;
}

.player__video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #000;
}

.player__loading,
.player__error {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space3);
  color: var(--color-text-secondary);
  width: min(80vw, 720px);
}

.player__error-title {
  color: #fff;
  font-size: var(--font-label-size);
}

.player__error-actions {
  display: flex;
  gap: var(--space2);
}

.player__controls {
  position: absolute;
  inset: auto 0 0;
  display: flex;
  flex-direction: column;
  gap: var(--space3);
  padding: var(--space4) var(--space6) var(--space5);
  background: linear-gradient(180deg, rgb(0 0 0 / 0%), rgb(0 0 0 / 62%)); /* taste-skill-ignore：视频上的中性遮罩，保证白色控制条可读 */
  color: #fff;
  opacity: 1;
  transition: opacity var(--duration-micro) ease;
}

.player__controls.is-hidden {
  opacity: 0;
  pointer-events: none;
}

.player__top {
  display: flex;
  align-items: center;
  gap: var(--space3);
}

.player__top :deep(.btn) {
  color: #fff;
}

.player__title {
  font-size: var(--font-caption-size);
  color: rgb(255 255 255 / 80%);
}

.player__bar {
  display: flex;
  align-items: center;
  gap: var(--space3);
}

.player__btn {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  color: #fff;
  transition: background var(--duration-micro) ease;
}

.player__btn:hover {
  background: rgb(255 255 255 / 14%);
}

.player__btn:focus-visible {
  outline: 2px solid #fff;
  outline-offset: 2px;
}

.player__time {
  font-size: var(--font-caption-size);
  color: rgb(255 255 255 / 80%);
  white-space: nowrap;
}

.player__seek {
  flex: 1;
  accent-color: var(--color-primary);
}

.player__select {
  height: 30px;
  padding: 0 var(--space2);
  border-radius: var(--radius-sm);
  border: 1px solid rgb(255 255 255 / 24%);
  background: rgb(0 0 0 / 40%);
  color: #fff;
  font-size: var(--font-caption-size);
}
</style>
