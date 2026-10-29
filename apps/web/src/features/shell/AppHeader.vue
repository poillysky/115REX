<script setup lang="ts">
// 全局顶栏（docs/03 §3）：左品牌，右侧通知 / 日志 / 账号。
// 页面入口不在这里，统一放侧栏 SideBar；顶栏只承载跨页面的全局信息。
// 铃铛展开「通知」面板（进行中的动作 + 近期动作记录），日志入口仍去动作记录所在页。
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppBadge from '@/features/shell/components/AppBadge.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppLogo from '@/features/shell/components/AppLogo.vue'
import { useSessionStore } from '@/application/session'
import { useActionStore } from '@/application/actions'

const router = useRouter()
const session = useSessionStore()
const actions = useActionStore()

const emit = defineEmits<{ 'toggle-sidebar': [] }>()

const accountOpen = ref(false)
const noticeOpen = ref(false)
const accountRoot = ref<HTMLElement | null>(null)
const noticeRoot = ref<HTMLElement | null>(null)

/** 动作队列未结束的条数，作为通知角标。 */
const activeCount = computed(() => actions.activeCount)

/** 通知面板内容：进行中的排前面，其余按时间倒序取最近 6 条 */
const noticeItems = computed(() =>
  [...actions.history]
    .sort((a, b) => {
      const live = (r: { status: string }) => (r.status === 'pending' || r.status === 'running' ? 1 : 0)
      return live(b) - live(a) || b.updatedAt - a.updatedAt
    })
    .slice(0, 6),
)

const KIND_LABEL: Record<string, string> = { transfer: '转存', push: '推送', download: '下载' }

function statusText(status: string): string {
  if (status === 'pending') return '排队中'
  if (status === 'running') return '进行中'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  return '已取消'
}

function statusTone(status: string): 'neutral' | 'success' | 'warning' | 'danger' {
  if (status === 'succeeded') return 'success'
  if (status === 'running' || status === 'pending') return 'warning'
  if (status === 'failed') return 'danger'
  return 'neutral'
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return new Date(ts).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

/** 两个浮层互斥：打开一个就收起另一个，避免叠在屏幕上 */
function toggleAccount(): void {
  accountOpen.value = !accountOpen.value
  noticeOpen.value = false
}

function toggleNotice(): void {
  noticeOpen.value = !noticeOpen.value
  accountOpen.value = false
}

function closeLayers(): void {
  accountOpen.value = false
  noticeOpen.value = false
}

/** 点击浮层外部收起；Esc 在任意位置收起（关闭优先于页面快捷键） */
function onPointerDown(event: PointerEvent): void {
  const target = event.target as Node
  if (accountOpen.value && !accountRoot.value?.contains(target)) accountOpen.value = false
  if (noticeOpen.value && !noticeRoot.value?.contains(target)) noticeOpen.value = false
}

function onKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && (accountOpen.value || noticeOpen.value)) {
    event.preventDefault()
    closeLayers()
  }
}

/** 菜单内上下方向键移动焦点，Home / End 跳到两端 */
function moveFocus(event: KeyboardEvent): void {
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
  const root = event.currentTarget as HTMLElement
  const items = Array.from(root.querySelectorAll<HTMLElement>('[role="menuitem"]'))
  if (!items.length) return
  event.preventDefault()
  const index = items.indexOf(document.activeElement as HTMLElement)
  const next =
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? items.length - 1
        : event.key === 'ArrowDown'
          ? (index + 1) % items.length
          : (index - 1 + items.length) % items.length
  items[next]?.focus()
}

function goAccount(): void {
  closeLayers()
  void router.push({ name: 'account' })
}

function goTheme(): void {
  closeLayers()
  void router.push({ name: 'account-theme' })
}

async function signOut(): Promise<void> {
  closeLayers()
  await session.logout()
  void router.replace({ name: 'login' })
}

function goHistory(): void {
  closeLayers()
  void router.push({ name: 'index' })
}

onMounted(() => {
  window.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('keydown', onKeydown)
  if (session.isAuthenticated && !session.me) void session.loadMe()
  if (!actions.history.length) void actions.loadHistory()
})

onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onPointerDown)
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <header class="topbar">
    <button
      class="topbar__menu-btn"
      type="button"
      aria-label="展开页面导航"
      @click="emit('toggle-sidebar')"
    >
      <AppIcon name="list" :size="20" />
    </button>

    <RouterLink class="topbar__brand" :to="{ name: 'index' }" aria-label="115REX 首页">
      <AppLogo :size="28" />
      <span class="topbar__brand-text">115REX</span>
    </RouterLink>

    <div class="topbar__toolbar">
      <div ref="noticeRoot" class="topbar__pop">
        <button
          class="topbar__tool"
          type="button"
          :class="{ 'is-open': noticeOpen }"
          :aria-expanded="noticeOpen"
          aria-haspopup="dialog"
          aria-label="通知"
          title="通知"
          @click="toggleNotice"
        >
          <AppIcon name="bell" :size="18" />
          <span v-if="activeCount" class="topbar__dot" aria-hidden="true" />
        </button>

        <Transition name="pop">
          <div v-if="noticeOpen" class="popover popover--notice" role="dialog" aria-label="通知">
            <header class="popover__head">
              <p class="popover__title">通知</p>
              <RouterLink class="popover__link" :to="{ name: 'system-115' }" @click="closeLayers">
                115网盘
              </RouterLink>
            </header>

            <ul v-if="noticeItems.length" class="notice">
              <li v-for="item in noticeItems" :key="item.id" class="notice__row">
                <span class="notice__kind">{{ KIND_LABEL[item.kind] ?? item.kind }}</span>
                <span class="notice__title">{{ item.title ?? item.ref }}</span>
                <AppBadge :tone="statusTone(item.status)">{{ statusText(item.status) }}</AppBadge>
                <span class="notice__time tabular">{{ relativeTime(item.updatedAt) }}</span>
              </li>
            </ul>
            <p v-else class="popover__empty">还没有动作记录。发起转存或下载后会出现在这里。</p>

            <footer class="popover__foot">
              <button type="button" class="popover__foot-btn" @click="goHistory">
                查看动作记录
              </button>
            </footer>
          </div>
        </Transition>
      </div>

      <RouterLink
        class="topbar__tool"
        :to="{ name: 'system-plugins' }"
        aria-label="日志"
        title="日志"
      >
        <AppIcon name="inbox" :size="18" />
      </RouterLink>

      <span class="topbar__sep" aria-hidden="true" />

      <div ref="accountRoot" class="topbar__pop">
        <button
          class="topbar__user"
          type="button"
          :class="{ 'is-open': accountOpen }"
          :aria-expanded="accountOpen"
          aria-haspopup="menu"
          @click="toggleAccount"
        >
          <span class="topbar__avatar" aria-hidden="true">
            <img v-if="session.avatarUrl" :src="session.avatarUrl" alt="" />
            <AppLogo v-else :size="28" tile />
          </span>
          <span class="topbar__user-name">{{ session.displayName || '未登录' }}</span>
          <AppIcon name="chevron-down" :size="14" class="topbar__user-arrow" />
        </button>

        <Transition name="pop">
          <div v-if="accountOpen" class="popover popover--menu" role="menu" @keydown="moveFocus">
            <div class="menu-head">
              <span class="menu-head__avatar" aria-hidden="true">
                <img v-if="session.avatarUrl" :src="session.avatarUrl" alt="" />
                <AppLogo v-else :size="32" tile />
              </span>
              <div class="menu-head__text">
                <p class="menu-head__name">{{ session.displayName || '未登录' }}</p>
                <p class="menu-head__meta">
                  {{ session.mockMode ? '演示环境' : '已连接服务器' }}
                </p>
              </div>
            </div>
            <div class="menu-list">
              <button class="menu-item" type="button" role="menuitem" @click="goAccount">
                <AppIcon name="user" :size="16" />
                <span>账号管理</span>
              </button>
              <button class="menu-item" type="button" role="menuitem" @click="goTheme">
                <AppIcon name="sparkles" :size="16" />
                <span>主题管理</span>
              </button>
              <button class="menu-item" type="button" role="menuitem" @click="signOut">
                <AppIcon name="logout" :size="16" />
                <span>退出登录</span>
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </header>
</template>

<style scoped>
/* 顶栏：实色 surface 架在内容台之上，用投影与底边和页面分开（docs/02 §5.2 / §6） */
.topbar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: var(--space3);
  height: var(--topbar-height);
  padding: 0 var(--space5);
  background: var(--chrome-surface);
  border-bottom: 1px solid var(--panel-border);
  box-shadow: var(--shadow-chrome-top);
}

.topbar__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space2);
  flex: none;
  padding: var(--space1) var(--space2) var(--space1) 0;
  border-radius: var(--radius-md);
  transition: opacity var(--duration-micro) ease;
}

.topbar__brand:hover {
  opacity: 0.82;
}

/* 侧栏开关只在侧栏折叠的档位出现 */
.topbar__menu-btn {
  display: none;
  place-items: center;
  flex: none;
  width: 36px;
  height: 36px;
  margin-left: calc(var(--space2) * -1);
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.topbar__menu-btn:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

/* 品牌字标：沿用 heading2 档（22/600），只收字距贴合 Logo 方块 */
.topbar__brand-text {
  font-size: var(--font-heading2-size);
  font-weight: var(--font-heading2-weight);
  letter-spacing: var(--font-heading2-tracking);
  line-height: 1;
  color: var(--color-text-primary);
}

/* 右侧工具区：通知 / 日志 / 账号 */
.topbar__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space1);
  margin-left: auto;
}

.topbar__sep {
  width: 1px;
  height: 20px;
  margin: 0 var(--space1);
  background: var(--color-border-soft);
}

.topbar__pop {
  position: relative;
}

.topbar__tool {
  position: relative;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  transition:
    color var(--duration-micro) ease,
    background-color var(--duration-micro) ease;
}

.topbar__tool:hover,
.topbar__tool.is-open {
  color: var(--color-text-primary);
  background: color-mix(in srgb, var(--color-surface-secondary) 82%, transparent);
}

.topbar__dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-surface); /* taste-skill-ignore：把未读点从图标笔画上切出来，不是装饰阴影 */
}

.topbar__user {
  display: inline-flex;
  align-items: center;
  gap: var(--space2);
  height: 36px;
  margin-left: var(--space1);
  padding: 0 var(--space2) 0 var(--space1);
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  background: color-mix(in srgb, var(--color-surface-secondary) 74%, transparent);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    border-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.topbar__user:hover,
.topbar__user.is-open {
  background: var(--color-surface-secondary);
  border-color: var(--color-border-soft);
  color: var(--color-text-primary);
}

.topbar__avatar {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  color: var(--color-text-primary);
  box-shadow: 0 0 0 1px var(--color-border-soft);
  font-size: var(--font-caption-size);
  font-weight: 600;
}

.topbar__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.topbar__user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.topbar__user-arrow {
  color: var(--color-text-secondary);
  transition: transform var(--duration-micro) ease;
}

.topbar__user.is-open .topbar__user-arrow {
  transform: rotate(180deg);
}

/* ---- 浮层：菜单与通知共用一套磨砂外观（Level 3 Overlay，docs/02 §6） ---- */
.popover {
  position: absolute;
  top: calc(100% + var(--space2));
  right: 0;
  padding: var(--space1);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-xl);
  background: var(--chrome-float);
  backdrop-filter: var(--chrome-blur);
  -webkit-backdrop-filter: var(--chrome-blur);
  box-shadow:
    inset 0 1px 0 var(--highlight-line),
    var(--shadow-overlay);
}

.popover--menu {
  width: 244px;
}

.popover--notice {
  width: 372px;
  max-width: calc(100vw - var(--space6));
  padding: 0;
  overflow: hidden;
}

.popover__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  padding: var(--space3) var(--space3) var(--space2);
}

/* 账号菜单头：头像 + 名称 + 环境，和徽标行用一条分隔线切开 */
.menu-head {
  display: flex;
  align-items: center;
  gap: var(--space2);
  padding: var(--space3);
  margin-bottom: var(--space1);
  border-bottom: 1px solid var(--panel-divider);
}

.menu-head__avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 32px;
  height: 32px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
}

.menu-head__avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.menu-head__text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.menu-head__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-label-size);
  font-weight: var(--font-label-weight);
  line-height: 1.3;
  color: var(--color-text-primary);
}

.menu-head__meta {
  font-size: var(--font-caption-size);
  line-height: 1.3;
  color: var(--color-text-tertiary);
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.popover--notice .popover__head {
  padding: var(--space4) var(--space4) var(--space2);
}

.popover__title {
  font-size: var(--font-caption-size);
  font-weight: 600;
  color: var(--color-text-primary);
}

.popover__meta {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.popover__link {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: color var(--duration-micro) ease;
}

.popover__link:hover {
  color: var(--color-text-primary);
}

.popover__empty {
  padding: var(--space4);
  font-size: var(--font-caption-size);
  line-height: 1.6;
  color: var(--color-text-secondary);
}

.popover__foot {
  display: flex;
  justify-content: flex-end;
  padding: var(--space2) var(--space3) var(--space3);
  border-top: 1px solid var(--panel-divider);
}

.popover__foot-btn {
  height: 28px;
  padding: 0 var(--space2);
  border-radius: var(--radius-sm);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.popover__foot-btn:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

/* 通知行：动作类型 + 标题 + 状态徽标 + 相对时间，一行一个，右侧时间对齐 */
.notice {
  display: flex;
  flex-direction: column;
  max-height: 320px;
  margin: 0;
  padding: var(--space1) var(--space2) var(--space2);
  overflow-y: auto;
  list-style: none;
}

.notice__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space2);
  padding: var(--space2);
  border-radius: var(--radius-sm);
}

.notice__row:hover {
  background: var(--color-surface-secondary);
}

.notice__kind {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.notice__title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.notice__time {
  grid-column: 3;
  font-size: var(--font-caption-size);
  color: var(--color-text-tertiary);
}

.notice__row > :deep(.badge) {
  max-width: 64px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--space3);
  width: 100%;
  height: 38px;
  padding: 0 var(--space3);
  border-radius: var(--radius-sm);
  font-size: var(--font-label-size);
  color: var(--color-text-secondary);
  text-align: left;
  transition:
    background-color var(--duration-micro) ease,
    color var(--duration-micro) ease;
}

.menu-item :deep(.icon) {
  color: var(--color-text-tertiary);
  transition: color var(--duration-micro) ease;
}

.menu-item:hover,
.menu-item:focus-visible {
  color: var(--color-text-primary);
  background: var(--color-surface-secondary);
}

.menu-item:hover :deep(.icon),
.menu-item:focus-visible :deep(.icon) {
  color: var(--color-text-primary);
}

/* 浮层出现：从顶部 4px 落下，不做缩放 */
.pop-enter-active,
.pop-leave-active {
  transition:
    opacity var(--duration-micro) ease,
    transform var(--duration-micro) ease;
}

.pop-enter-from,
.pop-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (max-width: 900px) {
  .topbar {
    padding: 0 var(--space4);
    gap: var(--space2);
  }
  .topbar__menu-btn {
    display: grid;
    width: 40px;
    height: 40px;
  }
  .topbar__tool {
    width: 38px;
    height: 38px;
  }
}

@media (max-width: 640px) {
  .topbar {
    padding: 0 var(--space3);
  }

  .topbar__brand-text,
  .topbar__user-name,
  .topbar__sep {
    display: none;
  }

  /* 窄屏浮层贴边展开，不超出视口 */
  .popover--notice {
    position: fixed;
    top: var(--topbar-height);
    right: var(--space3);
    left: var(--space3);
    width: auto;
    max-width: none;
  }
}
</style>
