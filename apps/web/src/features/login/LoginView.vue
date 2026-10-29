<script setup lang="ts">
// 登录 / 注册页（docs/02 §11 表单；docs/03 §3）。
// 品牌渐变只在这里与关于页出现，且整页只一处。
// 服务端一个账号都没有时 → 首次打开即注册；已有账号 → 登录，可手动切到注册入口。
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import AppLogo from '@/features/shell/components/AppLogo.vue'
import { useSessionStore } from '@/application/session'
import { describeError } from '@/core/api/error'

const REMEMBER_KEY = 'rex.remembered'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const confirm = ref('')
const errorText = ref('')
/** 勾选后同时记住用户名与密码（仅本机浏览器，明文存于 localStorage） */
const remember = ref(false)
const passwordVisible = ref(false)

/** 改密后跳回登录页时的一次性提示，看完即清掉 query，刷新不再出现 */
const notice = ref(
  route.query.passwordChanged === '1' ? '密码已更新，请用新密码重新登录。' : '',
)

const isRegister = computed(() => mode.value === 'register')
const submitText = computed(() => (isRegister.value ? '创建并进入' : '登录'))

interface Remembered {
  username: string
  password: string
}

function readRemembered(): Remembered | null {
  try {
    const raw = localStorage.getItem(REMEMBER_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<Remembered>
    if (!parsed.username || !parsed.password) return null
    return { username: parsed.username, password: parsed.password }
  } catch {
    return null
  }
}

function writeRemembered(value: Remembered | null): void {
  try {
    if (value) localStorage.setItem(REMEMBER_KEY, JSON.stringify(value))
    else localStorage.removeItem(REMEMBER_KEY)
  } catch {
    /* 隐私模式下忽略 */
  }
}

onMounted(async () => {
  if (notice.value) {
    void router.replace({ name: 'login', query: {} })
  }
  const remembered = readRemembered()
  if (remembered) {
    username.value = remembered.username
    password.value = remembered.password
    remember.value = true
  }
  await session.checkRegistration()
  if (session.registrationOpen && !remembered) mode.value = 'register'
})

function switchMode(): void {
  mode.value = isRegister.value ? 'login' : 'register'
  errorText.value = ''
  notice.value = ''
  confirm.value = ''
  passwordVisible.value = false
}

/** 忘记密码没有独立找回流程，切到注册入口等同于「换个账号/新建」，措辞上不下承诺 */
function switchToRegister(): void {
  if (isRegister.value) return
  switchMode()
}

async function submit(): Promise<void> {
  const name = username.value.trim()
  if (!name || !password.value) {
    errorText.value = '请输入用户名和密码'
    return
  }
  if (isRegister.value) {
    if (name.length < 3) {
      errorText.value = '用户名至少 3 个字符'
      return
    }
    if (password.value.length < 6) {
      errorText.value = '密码至少 6 位'
      return
    }
    if (password.value !== confirm.value) {
      errorText.value = '两次输入的密码不一致'
      return
    }
  }
  errorText.value = ''
  notice.value = ''
  try {
    if (isRegister.value) {
      await session.register(name, password.value)
    } else {
      await session.login(name, password.value)
    }
    writeRemembered(remember.value ? { username: name, password: password.value } : null)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/library'
    await router.replace(redirect)
  } catch (error) {
    errorText.value = describeError(error)
  }
}
</script>

<template>
  <div class="login">
    <!-- 氛围光晕：卡片背后一处品牌柔光，整页只这一处装饰光 -->
    <div class="login__glow" aria-hidden="true" />

    <!-- 底部波浪：三层错落，颜色全部由品牌 token 派生，随明暗与强调色变化 -->
    <div class="login__waves" aria-hidden="true">
      <svg class="login__wave login__wave--back" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path
          d="M0 176c160-58 320-72 480-40s320 96 480 96 320-80 480-112v200H0Z"
          fill="currentColor"
        />
      </svg>
      <svg class="login__wave login__wave--mid" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path
          d="M0 216c180-64 340-64 520-16s300 88 460 64 300-96 460-128v184H0Z"
          fill="currentColor"
        />
      </svg>
      <svg class="login__wave login__wave--front" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path
          d="M0 264c200-56 360-48 540-8s320 64 480 40 280-72 420-96v120H0Z"
          fill="currentColor"
        />
      </svg>
    </div>

    <main class="login__card">
      <header class="login__intro">
        <span class="login__mark">
          <AppLogo :size="88" tile />
        </span>
        <h1 class="login__title">115REX</h1>
      </header>

      <p v-if="notice" class="login__notice" role="status">
        <AppIcon name="check" :size="16" />
        <span>{{ notice }}</span>
      </p>

      <form class="login__form" @submit.prevent="submit">
        <label class="field">
          <span class="field__label">用户名</span>
          <span class="login__control">
            <AppIcon name="user" :size="18" class="login__control-icon" />
            <input
              v-model="username"
              class="field__input"
              autocomplete="username"
              autocapitalize="off"
              spellcheck="false"
              placeholder="请输入用户名"
              autofocus
            />
          </span>
        </label>

        <label class="field">
          <span class="field__label">密码</span>
          <span class="login__control">
            <AppIcon name="key" :size="18" class="login__control-icon" />
            <input
              v-model="password"
              class="field__input login__input--secret"
              :type="passwordVisible ? 'text' : 'password'"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
              placeholder="请输入密码"
            />
            <button
              type="button"
              class="login__eye"
              :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
              :aria-pressed="passwordVisible"
              @click="passwordVisible = !passwordVisible"
            >
              <AppIcon :name="passwordVisible ? 'eye-off' : 'eye'" :size="18" />
            </button>
          </span>
        </label>

        <label v-if="isRegister" class="field">
          <span class="field__label">确认密码</span>
          <span class="login__control">
            <AppIcon name="key" :size="18" class="login__control-icon" />
            <input
              v-model="confirm"
              class="field__input"
              type="password"
              autocomplete="new-password"
              placeholder="请再次输入密码"
            />
          </span>
        </label>

        <div v-if="!isRegister" class="login__options">
          <label class="login__remember">
            <input v-model="remember" type="checkbox" class="login__checkbox" />
            <span>保持登录</span>
          </label>
          <button type="button" class="login__forgot" @click="switchToRegister">
            忘记密码？
          </button>
        </div>

        <p v-if="errorText" class="login__error" role="alert">
          <AppIcon name="alert" :size="16" />
          <span>{{ errorText }}</span>
        </p>

        <AppButton variant="primary" type="submit" :loading="session.loading" class="login__submit">
          {{ submitText }}
        </AppButton>
      </form>

      <p class="login__switch">
        {{ isRegister ? '已有账号？' : '还没有账号？' }}
        <button type="button" class="login__switch-link" @click="switchMode">
          {{ isRegister ? '去登录' : '创建账号' }}
        </button>
      </p>
    </main>
  </div>
</template>

<style scoped>
/* 整屏：品牌浅渐变打底 + 底部波浪，卡片居中，给波浪留出呼吸区。
   用 svh 而不是 100%：登录页在 #app 之外单独铺满视口，矮屏也不会溢出。
   底部留白取「视口高 - 卡片与间距」，矮屏自动收窄，不会撑出滚动条。 */
.login {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 100svh;
  padding: var(--space6) var(--space6) clamp(var(--space6), 15svh, 120px);
  overflow: hidden;
  background: var(--gradient-brand-soft); /* taste-skill-ignore：登录是唯一保留品牌氛围的整屏，docs/02 §3.1.1 */
  caret-color: var(--color-primary);
}

/* 卡片背后柔光：用 primary-subtle 扩散，不引入第二处 brandGradient */
.login__glow {
  position: absolute;
  top: 40%;
  left: 50%;
  width: min(78vw, 560px);
  height: min(58vw, 420px);
  transform: translate(-50%, -52%);
  pointer-events: none;
  background: radial-gradient(
    ellipse at center,
    color-mix(in srgb, var(--color-primary) 22%, transparent) 0%,
    color-mix(in srgb, var(--color-primary-subtle) 65%, transparent) 38%,
    transparent 74%
  );
  filter: blur(4px);
}

/* 波浪容器：贴在底部，高度随视口，窄屏压扁一些免得盖住卡片 */
.login__waves {
  position: absolute;
  inset: auto 0 0 0;
  height: min(38vh, 320px);
  pointer-events: none;
}

.login__wave {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  will-change: transform;
}

/* 三层由远及近：越靠前越实，色相统一取品牌色，明暗各自成立 */
.login__wave--back {
  color: color-mix(in srgb, var(--color-primary-subtle) 70%, transparent);
}

.login__wave--mid {
  color: color-mix(in srgb, var(--color-primary) 14%, var(--color-primary-subtle));
}

.login__wave--front {
  color: color-mix(in srgb, var(--color-primary) 26%, transparent);
  opacity: 0.55;
}

/* 卡片：透明磨砂玻璃——低不透明度表面 + 强模糊，透过看得到背景柔光与波浪 */
.login__card {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 400px;
  padding: var(--space8) var(--space8) var(--space6);
  border-radius: var(--radius2xl);
  border: 1px solid color-mix(in srgb, var(--highlight-line) 70%, var(--color-border-soft));
  background: color-mix(in srgb, var(--color-surface) 52%, transparent);
  backdrop-filter: blur(32px) saturate(1.4);
  -webkit-backdrop-filter: blur(32px) saturate(1.4);
  box-shadow:
    inset 0 1px 0 var(--highlight-line),
    inset 0 0 0 1px color-mix(in srgb, var(--color-surface) 35%, transparent),
    0 1px 2px color-mix(in srgb, var(--color-text-primary) 5%, transparent),
    0 12px 32px color-mix(in srgb, var(--color-text-primary) 8%, transparent),
    0 32px 72px color-mix(in srgb, var(--color-primary) 10%, transparent);
}

/* 品牌区：Logo 带轻阴影托住，字标紧随其后 */
.login__intro {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space3);
  text-align: center;
}

.login__mark {
  display: grid;
  place-items: center;
}

.login__title {
  font-size: var(--font-heading2-size);
  font-weight: var(--font-heading2-weight);
  letter-spacing: var(--font-heading2-tracking);
  line-height: 1.2;
  color: var(--color-text-primary);
}

.login__notice,
.login__error {
  display: flex;
  align-items: flex-start;
  gap: var(--space2);
  margin-top: var(--space5);
  padding: var(--space2) var(--space3);
  border-radius: var(--radius-md);
  font-size: var(--font-caption-size);
  line-height: 1.6;
}

.login__notice {
  background: color-mix(in srgb, var(--color-success) 12%, transparent);
  color: var(--color-success);
}

.login__error {
  margin-top: 0;
  background: color-mix(in srgb, var(--color-danger) 10%, transparent);
  color: var(--color-danger);
}

/* 图标与首行对齐，不随换行下沉 */
.login__notice :deep(.icon),
.login__error :deep(.icon) {
  margin-top: 2px;
}

.login__form {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
  margin-top: var(--space6);
}

/* 标签贴控件更近，字段之间仍用 form 的 gap，上下节奏一致 */
.login__form .field {
  gap: var(--space1);
}

.login__form .field__label {
  padding-left: var(--space1);
}

/* 输入框：左侧内嵌语义图标，密码框右侧留给眼睛按钮 */
.login__control {
  position: relative;
  display: block;
}

.login__control .field__input {
  padding-left: calc(var(--space3) + 26px);
  /* 磨砂卡上输入区略实一点，保证可读 */
  background: color-mix(in srgb, var(--color-surface) 78%, var(--color-surface-secondary));
  border-color: color-mix(in srgb, var(--color-separator) 55%, transparent);
  transition:
    border-color var(--duration-micro) ease,
    background-color var(--duration-micro) ease,
    outline-color var(--duration-micro) ease;
}

/* 焦点环沿用全局 :focus-visible，边框略提亮保证磨砂卡上可读（docs/02 §10 / 03 §7） */
.login__control .field__input:focus-visible {
  background: color-mix(in srgb, var(--color-surface) 92%, transparent);
  border-color: color-mix(in srgb, var(--color-primary) 36%, var(--color-separator));
}

.login__input--secret {
  padding-right: calc(var(--space3) + 24px);
}

.login__control-icon {
  position: absolute;
  top: 50%;
  left: var(--space3);
  transform: translateY(-50%);
  color: var(--color-text-tertiary);
  pointer-events: none;
}

.login__eye {
  position: absolute;
  top: 50%;
  right: var(--space2);
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  transform: translateY(-50%);
  border-radius: var(--radius-sm);
  color: var(--color-text-tertiary);
  transition:
    color var(--duration-micro) ease,
    background-color var(--duration-micro) ease;
}

.login__eye:hover {
  color: var(--color-text-primary);
  background: color-mix(in srgb, var(--color-surface-secondary) 80%, transparent);
}

.login__eye:focus-visible {
  outline: 2px solid color-mix(in srgb, var(--color-primary) 40%, transparent);
  outline-offset: 1px;
}

/* 保持登录 + 忘记密码同排，两端对齐：左侧个人偏好，右侧补救入口 */
.login__options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  margin-top: calc(var(--space1) * -1);
}

.login__remember {
  display: inline-flex;
  align-items: center;
  gap: var(--space2);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  cursor: pointer;
  user-select: none;
}

.login__checkbox {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: var(--color-primary);
  cursor: pointer;
}

.login__forgot {
  font-size: var(--font-caption-size);
  color: var(--color-primary);
  transition: opacity var(--duration-micro) ease;
}

.login__forgot:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
  opacity: 0.85;
}

.login__submit {
  width: 100%;
  min-height: 44px;
  margin-top: var(--space2);
}

/* 模式切换：正文级链接，不放成灰底按钮，避免与主按钮争焦点 */
.login__switch {
  margin-top: var(--space5);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  text-align: center;
}

.login__switch-link {
  font-weight: var(--font-label-weight);
  color: var(--color-primary);
  text-underline-offset: 3px;
}

.login__switch-link:hover {
  text-decoration: underline;
}

/* 窄屏：卡片贴边、内边距收一档，波浪压到很浅避免与表单打架 */
@media (max-width: 640px) {
  .login {
    padding: var(--space5) var(--space4) clamp(var(--space4), 10svh, 72px);
    place-items: start center;
  }

  .login__card {
    padding: var(--space6) var(--space5) var(--space5);
    border-radius: var(--radius-xl);
  }

  .login__glow {
    width: min(90vw, 420px);
    height: min(70vw, 300px);
  }

  .login__waves {
    height: min(26vh, 200px);
  }
}

/* 矮屏（如 1280×640 的笔记本）：收起部分留白，保证整页不出现滚动条 */
@media (max-height: 720px) and (min-width: 641px) {
  .login {
    padding-bottom: var(--space6);
    align-content: start;
  }

  .login__card {
    padding: var(--space6) var(--space8) var(--space5);
  }

  .login__form {
    gap: var(--space3);
    margin-top: var(--space5);
  }

  .login__switch {
    margin-top: var(--space4);
  }

  .login__glow {
    opacity: 0.7;
  }
}

@media (prefers-reduced-motion: no-preference) {
  .login__card {
    animation: login-rise var(--duration-page) cubic-bezier(0.22, 1, 0.36, 1) both;
  }

  .login__mark {
    animation: login-mark var(--duration-page) cubic-bezier(0.22, 1, 0.36, 1) both;
    animation-delay: 40ms;
  }

  .login__wave--back {
    animation: login-wave 18s ease-in-out infinite alternate;
  }

  .login__wave--mid {
    animation: login-wave 14s ease-in-out infinite alternate-reverse;
  }

  .login__wave--front {
    animation: login-wave 11s ease-in-out infinite alternate;
  }

  @keyframes login-rise {
    from {
      opacity: 0;
      transform: translateY(14px);
    }
  }

  @keyframes login-mark {
    from {
      opacity: 0;
      transform: translateY(6px) scale(0.96);
    }
  }

  @keyframes login-wave {
    from {
      transform: translateX(-1.5%) scaleX(1.02);
    }
    to {
      transform: translateX(1.5%) scaleX(1.02);
    }
  }
}
</style>
