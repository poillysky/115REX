<script setup lang="ts">
// 系统分组页共用样式：分组卡片 / 行 / 开关 / 表单 / 二次确认。
// 只做样式，不带逻辑；各页面通过 <SettingsSection> 使用。
</script>

<template>
  <div class="sys">
    <slot />
  </div>
</template>

<style>
/* 这些类名由系统分组页在 scoped 之外共用，故不加 scoped */
/* 分组：标题与说明横跨整行，内容卡片在下方 —— 说明不再挤在左侧窄栏 */
.sys .group {
  display: flex;
  flex-direction: column;
  gap: var(--space2);
}

.sys .group__head {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 var(--space1);
}

.sys .group__title {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  letter-spacing: var(--font-heading3-tracking);
  line-height: 1.3;
  color: var(--color-text-primary);
}

.sys .group__desc {
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.sys .group + .group {
  margin-top: var(--space5);
}

/* Level 1 面板：边框 / 高光对齐弹窗卡（docs/02 §5.2 / §6.1） */
.sys .group__body {
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-xl);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

/* 表单型分组体：行内可能有输入框，留出内边距 */
.sys .group__body--form {
  padding: var(--space4);
}

.sys .row {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space2) var(--space3);
  min-height: 44px;
}

/* 表单行：左说明右控件，说明列固定，控件列占满 */
.sys .group__body--form .row {
  display: grid;
  grid-template-columns: 176px minmax(0, 1fr);
  gap: var(--space3);
  align-items: center;
  padding: var(--space2) 0;
}

.sys .group__body--form .row + .row {
  border-top: 1px solid var(--panel-divider);
}

.sys .row + .row {
  border-top: 1px solid var(--panel-divider);
}

.sys .row__label {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
  font-size: var(--font-caption-size);
}

.sys .row__hint {
  display: block;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

/* 长地址单行省略，hover 看全文 */
.sys .row__hint--url {
  max-width: 380px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-text-secondary);
}

.sys .row__value {
  display: flex;
  align-items: center;
  gap: var(--space2);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.sys .row__note {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.sys .row__error {
  padding: var(--space2) var(--space4);
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.sys .row__empty {
  padding: var(--space4);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.sys .row--form {
  display: block;
}

.sys .form {
  display: flex;
  align-items: flex-end;
  gap: var(--space3);
  flex-wrap: wrap;
}

.sys .form__field {
  display: flex;
  flex: 1 1 200px;
  flex-direction: column;
  gap: var(--space1);
  min-width: 0;
}

.sys .form__field--wide {
  flex: 2 1 320px;
}

.sys .form__field--full {
  flex: 1 1 100%;
}

.sys .form--stack {
  flex-direction: column;
  align-items: stretch;
  flex-wrap: nowrap;
}

.sys .form__label {
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

/* 输入框外观统一走 base.css 的 .field__input；系统页信息密，收敛到 36 高 */
.sys .form__input {
  height: 36px;
}

/* 多行输入：地址一行一个 */
.sys .form__textarea {
  height: auto;
  min-height: 76px;
  padding: var(--space2);
  font-family: inherit;
  line-height: 1.6;
  resize: vertical;
}

.sys .form__actions {
  display: flex;
  gap: var(--space2);
}

.sys .confirm {
  display: flex;
  align-items: center;
  gap: var(--space3);
  flex-wrap: wrap;
  padding: var(--space3) var(--space4);
  border-top: 1px solid var(--panel-divider);
  background: color-mix(in srgb, var(--color-danger) 6%, transparent);
}

.sys .confirm__text {
  flex: 1;
  font-size: var(--font-caption-size);
  color: var(--color-danger);
}

.sys .confirm__actions {
  display: flex;
  gap: var(--space2);
}

/* ---- 通用卡片骨架：标题区节奏对齐弹窗 head */
.sys .card {
  display: flex;
  flex-direction: column;
  border-radius: var(--radius-xl);
  border: 1px solid var(--panel-border);
  background: var(--color-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.sys .card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  padding: var(--space5) var(--space6) var(--space4);
  border-bottom: 1px solid var(--panel-divider);
}

.sys .card__head-main {
  display: flex;
  flex-direction: column;
  gap: var(--space1);
  min-width: 0;
}

.sys .card__title {
  font-size: var(--font-heading3-size);
  font-weight: var(--font-heading3-weight);
  letter-spacing: var(--font-heading3-tracking);
  line-height: 1.3;
  color: var(--color-text-primary);
}

.sys .card__desc {
  font-size: var(--font-caption-size);
  line-height: 1.5;
  color: var(--color-text-secondary);
}

.sys .card__action {
  display: inline-flex;
  align-items: center;
  gap: var(--space1);
  height: 28px;
  padding: 0 var(--space2);
  border-radius: var(--radius-sm);
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
  transition: background-color var(--duration-micro) ease, color var(--duration-micro) ease;
}

.sys .card__action:hover {
  background: var(--color-surface-secondary);
  color: var(--color-text-primary);
}

.sys .card__action:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 1px;
}

.sys .card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space4);
  padding: var(--space5) var(--space6);
}

/* 卡身里的行不再自带横向内边距，避免与卡体内边距叠加 */
.sys .card__body .row {
  padding: 0;
}

.sys .card__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space3);
  min-height: 56px;
  padding: var(--space3) var(--space6) var(--space5);
  border-top: 1px solid var(--panel-divider);
  background: color-mix(in srgb, var(--color-surface-secondary) 55%, transparent);
}

.sys .card__status {
  min-width: 0;
}

.sys .card__buttons {
  display: flex;
  align-items: center;
  gap: var(--space2);
  margin-left: auto;
}

@media (max-width: 900px) {
  .sys .card__head,
  .sys .card__body,
  .sys .card__actions {
    padding-left: var(--space4);
    padding-right: var(--space4);
  }
}

/* 子页面入口：整行可点，右侧箭头提示进入下一层 */
.sys .subpage {
  display: flex;
  align-items: center;
  gap: var(--space3);
  padding: var(--space2) var(--space3);
  min-height: 44px;
  color: inherit;
  text-decoration: none;
  transition: background-color var(--duration-micro) ease;
}

.sys .subpage:hover {
  background: var(--color-surface-secondary);
}

.sys .subpage:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: -2px;
}

.sys .subpage__main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.sys .subpage__label {
  font-size: var(--font-caption-size);
}

/* 开关：胶囊轨道 + 圆形滑块 */
.sys .switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  cursor: pointer;
}

.sys .switch input {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  margin: 0;
  cursor: pointer;
}

.sys .switch__track {
  width: 40px;
  height: 24px;
  border-radius: var(--radius-full);
  background: var(--color-surface-secondary);
  border: 1px solid var(--color-separator);
  transition: background-color var(--duration-micro) ease;
}

.sys .switch__track::after {
  content: '';
  display: block;
  width: 18px;
  height: 18px;
  margin: 2px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  transition: transform var(--duration-micro) ease;
}

.sys .switch input:checked + .switch__track {
  background: var(--color-primary);
  border-color: var(--color-primary);
}

.sys .switch input:checked + .switch__track::after {
  transform: translateX(16px);
}

.sys .switch input:focus-visible + .switch__track {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

@media (max-width: 900px) {
  .sys .group__body--form .row {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space2);
  }
}
</style>
