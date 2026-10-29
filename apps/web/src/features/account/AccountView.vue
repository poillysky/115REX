<script setup lang="ts">
// 账号管理页（docs/03 §3 / §10）：只放与「我这个账号」相关的设置。
// 头像与昵称走 PATCH /auth/profile；改密走 PUT /auth/password，成功后强制重新登录。
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import AppButton from '@/features/shell/components/AppButton.vue'
import AppDialog from '@/features/shell/components/AppDialog.vue'
import AppIcon from '@/features/shell/components/AppIcon.vue'
import IconLibraryPicker from '@/features/account/IconLibraryPicker.vue'
import { describeError } from '@/core/api/error'
import { useNotifyStore } from '@/application/notify'
import { useSessionStore } from '@/application/session'

const AVATAR_MAX_BYTES = 2 * 1024 * 1024
const AVATAR_SIZE = 256
const NAME_MAX = 32
const PASSWORD_MIN = 6

const router = useRouter()
const session = useSessionStore()
const notify = useNotifyStore()

const nameDraft = ref(session.displayName)
const nameSaving = ref(false)
const nameError = ref('')
const nameSaved = ref(false)

const avatarInput = ref<HTMLInputElement | null>(null)
const avatarSaving = ref(false)
const avatarError = ref('')
const pickerOpen = ref(false)

const passwordOpen = ref(false)
const currentPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const passwordSaving = ref(false)
const passwordError = ref('')

function openPasswordDialog(): void {
  currentPassword.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  passwordError.value = ''
  passwordOpen.value = true
}

const nameDirty = computed(() => nameDraft.value.trim() !== session.displayName)

// me 异步到位后回填一次草稿
watch(
  () => session.displayName,
  (value) => {
    if (!nameSaving.value) nameDraft.value = value
  },
)

async function saveName(): Promise<void> {
  const value = nameDraft.value.trim()
  nameError.value = ''
  nameSaved.value = false
  if (value.length > NAME_MAX) {
    nameError.value = `昵称最多 ${NAME_MAX} 个字符`
    return
  }
  nameSaving.value = true
  try {
    await session.updateProfile({ displayName: value })
    nameSaved.value = true
  } catch (error) {
    nameError.value = describeError(error)
  } finally {
    nameSaving.value = false
  }
}

/** 居中裁成正方形再缩到 256，避免把几 MB 的原图塞给后端。 */
async function resizeToDataUrl(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file)
  const side = Math.min(bitmap.width, bitmap.height)
  const canvas = document.createElement('canvas')
  canvas.width = AVATAR_SIZE
  canvas.height = AVATAR_SIZE
  const context = canvas.getContext('2d')
  if (!context) throw new Error('canvas unavailable')
  context.drawImage(
    bitmap,
    (bitmap.width - side) / 2,
    (bitmap.height - side) / 2,
    side,
    side,
    0,
    0,
    AVATAR_SIZE,
    AVATAR_SIZE,
  )
  bitmap.close()
  return canvas.toDataURL('image/png')
}

async function onAvatarPicked(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  avatarError.value = ''
  if (!file.type.startsWith('image/')) {
    avatarError.value = '请选择图片文件'
    return
  }
  if (file.size > AVATAR_MAX_BYTES) {
    avatarError.value = '图片不能超过 2 MB'
    return
  }

  avatarSaving.value = true
  try {
    const dataUrl = await resizeToDataUrl(file)
    await session.updateProfile({ avatarUrl: dataUrl })
    notify.success('头像已更新')
  } catch (error) {
    avatarError.value = describeError(error)
  } finally {
    avatarSaving.value = false
  }
}

/** 图标库里的地址是远程图片，交给后端抓取落盘后同样按本地头像返回。 */
async function pickFromLibrary(url: string): Promise<void> {
  avatarError.value = ''
  avatarSaving.value = true
  try {
    await session.updateProfile({ avatarUrl: url })
    notify.success('头像已更新')
  } catch (error) {
    avatarError.value = describeError(error)
  } finally {
    avatarSaving.value = false
  }
}

async function savePassword(): Promise<void> {
  passwordError.value = ''
  if (newPassword.value.length < PASSWORD_MIN) {
    passwordError.value = `新密码至少 ${PASSWORD_MIN} 位`
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  passwordSaving.value = true
  try {
    await session.changePassword(currentPassword.value, newPassword.value)
    await router.replace({ name: 'login', query: { passwordChanged: '1' } })
  } catch (error) {
    passwordError.value = describeError(error)
  } finally {
    passwordSaving.value = false
  }
}
</script>

<template>
  <div class="account">
    <!-- 头像 -->
    <section class="group">
      <div class="group__head">
        <h2 class="group__title">头像</h2>
        <p class="group__desc">可以上传本地图片，也可以从已启用的图标库里挑一个。</p>
      </div>
      <div class="group__body">
        <div class="row row--avatar">
          <span class="avatar" :class="{ 'avatar--busy': avatarSaving }">
            <img v-if="session.avatarUrl" :src="session.avatarUrl" :alt="`${session.displayName} 的头像`" />
            <span v-else class="avatar__initial" aria-hidden="true">{{ session.initial }}</span>
          </span>
          <div class="row__stack">
            <div class="row__actions">
              <AppButton variant="primary" :loading="avatarSaving" @click="avatarInput?.click()">
                上传图片
              </AppButton>
              <AppButton :disabled="avatarSaving" @click="pickerOpen = true">
                <AppIcon name="image" :size="15" />
                从图标库选择
              </AppButton>
            </div>
            <p v-if="avatarError" class="row__error">{{ avatarError }}</p>
            <p v-else class="row__note">PNG / JPG，最大 2 MB；方图取中心裁切，保存为 256×256。</p>
          </div>
        </div>
        <input
          ref="avatarInput"
          class="visually-hidden"
          type="file"
          accept="image/*"
          aria-label="选择头像图片"
          @change="onAvatarPicked"
        />
      </div>
    </section>

    <!-- 资料 -->
    <section class="group">
      <div class="group__head">
        <h2 class="group__title">资料</h2>
        <p class="group__desc">昵称只影响显示，登录仍用创建时设的用户名。</p>
      </div>
      <div class="group__body">
        <div class="row row--grid">
          <label class="field">
            <span class="field__label">用户名</span>
            <input class="field__input" type="text" :value="session.user?.username ?? ''" disabled />
            <span class="field__hint">创建后不可修改</span>
          </label>

          <label class="field">
            <span class="field__label">昵称</span>
            <input
              v-model="nameDraft"
              class="field__input"
              type="text"
              :maxlength="NAME_MAX"
              placeholder="留空则显示用户名"
              @keyup.enter="nameDirty && saveName()"
            />
            <span v-if="nameError" class="field__hint field__hint--error">{{ nameError }}</span>
            <span v-else-if="nameSaved" class="field__hint field__hint--ok">已保存</span>
            <span v-else class="field__hint">最多 {{ NAME_MAX }} 个字符</span>
          </label>

          <div class="field--actions">
            <AppButton
              variant="primary"
              :disabled="!nameDirty"
              :loading="nameSaving"
              @click="saveName"
            >
              保存
            </AppButton>
            <AppButton v-if="nameDirty" @click="nameDraft = session.displayName">
              撤销
            </AppButton>
          </div>
        </div>
      </div>
    </section>

    <!-- 安全：入口一行，改密进弹窗，避免三行表单撑开分组卡 -->
    <section class="group">
      <div class="group__head">
        <h2 class="group__title">安全</h2>
        <p class="group__desc">修改后所有设备都要重新登录，当前页面会跳回登录页。</p>
      </div>
      <div class="group__body">
        <div class="row">
          <span class="row__label">
            登录密码
            <span class="row__hint">定期更换可降低共用设备上的风险</span>
          </span>
          <span class="row__value">
            <AppButton size="sm" @click="openPasswordDialog">修改密码</AppButton>
          </span>
        </div>
      </div>
    </section>

    <AppDialog
      v-model:open="passwordOpen"
      title="修改密码"
      description="提交后所有设备都要重新登录。"
      size="sm"
    >
      <div class="password">
        <label class="field">
          <span class="field__label">当前密码</span>
          <input v-model="currentPassword" class="field__input" type="password" autocomplete="current-password" />
        </label>
        <label class="field">
          <span class="field__label">新密码</span>
          <input v-model="newPassword" class="field__input" type="password" autocomplete="new-password" />
          <span class="field__hint">至少 {{ PASSWORD_MIN }} 位</span>
        </label>
        <label class="field">
          <span class="field__label">确认新密码</span>
          <input v-model="confirmPassword" class="field__input" type="password" autocomplete="new-password" />
        </label>
        <p v-if="passwordError" class="row__error">{{ passwordError }}</p>
      </div>
      <template #footer>
        <AppButton size="sm" @click="passwordOpen = false">取消</AppButton>
        <AppButton
          size="sm"
          variant="primary"
          :loading="passwordSaving"
          :disabled="!currentPassword || !newPassword"
          @click="savePassword"
        >
          确认修改
        </AppButton>
      </template>
    </AppDialog>

    <IconLibraryPicker v-model:open="pickerOpen" @pick="pickFromLibrary" />
  </div>
</template>

<style scoped>
.account {
  display: flex;
  flex-direction: column;
  gap: var(--space5);
  /* 宽度与内边距由 AppShell 统一处理；页面只排自己的垂直节奏 */
  padding: 0;
}

.password {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
}

.row__label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.row__hint {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.row__value {
  display: flex;
  align-items: center;
  gap: var(--space2);
  flex: none;
}

/* 说明在卡片上方，卡片吃掉整行宽度（与 SysStyles 的分组头一致） */
.group {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
}

.group__head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--space1);
}

.group__title {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  letter-spacing: var(--font-heading3-tracking);
  line-height: 1.3;
}

.group__desc {
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

/* Level 1 面板，边框质感对齐弹窗（docs/02 §5.2） */
.group__body {
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-xl);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.row {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space3) var(--space5);
  min-height: 44px;
}

.row + .row {
  border-top: 1px solid var(--panel-divider);
}

/* 一行两列：窄屏自动收成一列 */
.row--grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space4) var(--space6);
  align-items: start;
}

.row__stack {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
  min-width: 0;
}

.row__actions {
  display: flex;
  align-items: center;
  gap: var(--space3);
  flex-wrap: wrap;
}

.row__note {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.row__error {
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.row--avatar {
  align-items: center;
  gap: var(--space5);
  padding: var(--space5) var(--space4);
}

/* 头像：圆形裁切，未设置时用首字母 + 中性面，不上渐变 */
.avatar {
  display: grid;
  place-items: center;
  flex: none;
  width: 88px;
  height: 88px;
  overflow: hidden;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  box-shadow:
    inset 0 0 0 1px var(--color-border-soft),
    0 0 0 4px color-mix(in srgb, var(--color-surface-secondary) 60%, transparent);
  transition: background-color var(--duration-page) ease;
}

/* 上传中：中性面 + 次要文字，不整体降透明度（docs/02 §12） */
.avatar--busy {
  background: var(--color-separator);
  color: var(--color-text-secondary);
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar__initial {
  font-size: var(--font-heading2-size);
  font-weight: var(--font-heading1-weight);
  letter-spacing: var(--font-heading2-tracking);
  color: var(--color-text-secondary);
}

.field--inline {
  flex-direction: row;
  align-items: center;
  gap: var(--space2);
}

/* 按钮组独占一行，与输入框左对齐 */
.field--actions {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  gap: var(--space2);
}

/* 跨两列：无需成对排的字段与错误提示 */
.field--wide {
  grid-column: 1 / -1;
}

@media (max-width: 720px) {
  .row--grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
