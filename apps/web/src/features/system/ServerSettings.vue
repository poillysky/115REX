<script setup lang="ts">
// 服务端（系统 → 设定 → 服务端 tab）：只读展示当前连接的服务端版本、存储与能力开关，
// 以及按版本一行一条的版本记录。
import { computed } from 'vue'

import AppBadge from '@/features/shell/components/AppBadge.vue'
import SysStyles from '@/features/shell/components/SysStyles.vue'
import { useSessionStore } from '@/application/session'

import { SERVER_RELEASES } from './server-releases'

const session = useSessionStore()

const currentVersion = computed(() => session.me?.server.version ?? '—')
const storageProvider = computed(() => session.me?.server.storageProvider ?? '—')

const capabilityRows = computed(() => {
  const caps = session.capabilities
  return [
    { label: '搜索', value: caps.search, hint: '聚合资源检索' },
    { label: '转存', value: caps.transfer, hint: '资源转存到网盘' },
    { label: '推送', value: caps.push, hint: '推送到下载器' },
    { label: '下载', value: caps.download, hint: '服务端代下' },
    { label: '播放', value: caps.play && caps.playbackAdapterReady, hint: '签发直链播放' },
  ]
})

const releases = computed(() =>
  SERVER_RELEASES.map((item) => ({
    ...item,
    current: item.version === session.me?.server.version,
  })),
)

function formatDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (!match) return iso
  return `${match[1]}.${match[2]}.${match[3]}`
}
</script>

<template>
  <SysStyles>
    <section class="group">
      <div class="card">
        <header class="card__head">
          <div class="card__head-main">
            <h2 class="card__title">服务端</h2>
            <p class="card__desc">当前连接的版本、存储与能力开关</p>
          </div>
          <AppBadge v-if="session.mockMode" tone="warning">演示数据</AppBadge>
        </header>

        <div class="card__body card__body--list">
          <ul class="rows" aria-label="服务端概况">
            <li class="row-item">
              <span class="row-item__label">版本</span>
              <span class="row-item__value tabular">{{ currentVersion }}</span>
            </li>
            <li class="row-item">
              <span class="row-item__label">存储</span>
              <span class="row-item__value">{{ storageProvider }}</span>
            </li>
          </ul>

          <div class="block">
            <h3 class="block__title">能力</h3>
            <ul class="caps" aria-label="能力开关">
              <li v-for="cap in capabilityRows" :key="cap.label" class="cap">
                <span class="cap__label" :title="cap.hint">{{ cap.label }}</span>
                <span class="chip" :class="{ 'is-off': !cap.value }">
                  {{ cap.value ? '可用' : '不可用' }}
                </span>
              </li>
            </ul>
          </div>

          <div class="block">
            <h3 class="block__title">版本记录</h3>
            <ul class="rows" aria-label="版本记录">
              <li
                v-for="item in releases"
                :key="item.version"
                class="row-item release"
                :class="{ 'is-current': item.current }"
              >
                <span class="release__ver tabular">{{ item.version }}</span>
                <time class="release__date" :datetime="item.date">{{ formatDate(item.date) }}</time>
                <span class="release__note" :title="item.note">{{ item.note }}</span>
                <span v-if="item.current" class="chip">当前</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  </SysStyles>
</template>

<style scoped>
/* 本页只读信息密，压缩行高与分区间距 */
:deep(.card__head) {
  padding-top: var(--space4);
  padding-bottom: var(--space3);
}

.card__body--list {
  gap: 0;
  padding: 0;
}

.rows,
.caps {
  list-style: none;
  margin: 0;
  padding: 0;
}

.row-item {
  display: flex;
  align-items: center;
  gap: var(--space3);
  min-height: 40px;
  padding: var(--space2) var(--space6);
  border-top: 1px solid var(--panel-divider);
}

.row-item:first-child {
  border-top: 0;
}

.row-item__label {
  flex: none;
  width: 40px;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.row-item__value {
  flex: 1;
  min-width: 0;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.tabular {
  font-variant-numeric: tabular-nums;
}

.block {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--panel-divider);
}

.block__title {
  margin: 0;
  padding: var(--space3) var(--space6) var(--space1);
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-secondary);
  letter-spacing: 0.02em;
}

.caps {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--space2);
  padding: var(--space2) var(--space6) var(--space4);
}

.cap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space1);
  min-height: 36px;
  padding: 0 var(--space2);
  border-radius: var(--radius-md);
  border: 1px solid var(--panel-border);
  background: var(--color-surface-secondary);
}

.cap__label {
  font-size: var(--font-caption-size);
  color: var(--color-text-primary);
}

.release.is-current {
  background: color-mix(in srgb, var(--color-primary-subtle) 55%, transparent);
}

.release__ver {
  flex: none;
  min-width: 48px;
  font-size: var(--font-caption-size);
  font-weight: var(--font-label-weight);
  color: var(--color-text-primary);
}

.release__date {
  flex: none;
  font-size: var(--font-caption-size);
  font-variant-numeric: tabular-nums;
  color: var(--color-text-secondary);
}

.release__note {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--font-caption-size);
  color: var(--color-text-secondary);
}

.chip {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 var(--space2);
  border-radius: var(--radius-full);
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  font-size: var(--font-caption-size);
  line-height: 1;
  white-space: nowrap;
}

.chip.is-off {
  background: var(--color-surface);
  color: var(--color-text-secondary);
  border: 1px solid var(--panel-border);
}

@media (max-width: 900px) {
  .row-item,
  .caps {
    padding-left: var(--space4);
    padding-right: var(--space4);
  }

  .block__title {
    padding-left: var(--space4);
    padding-right: var(--space4);
  }

  .caps {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .release {
    flex-wrap: wrap;
    row-gap: var(--space1);
  }

  .release__note {
    flex-basis: 100%;
    white-space: normal;
  }
}

@media (max-width: 560px) {
  .caps {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
