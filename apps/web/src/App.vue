<script setup lang="ts">
// 根组件：按路由 meta.bare 决定是否套导航外壳；轻提示全局只挂一份。
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppShell from '@/features/shell/AppShell.vue'
import AppToast from '@/features/shell/components/AppToast.vue'

const route = useRoute()
const bare = computed(() => Boolean(route.meta.bare))
</script>

<template>
  <RouterView v-if="bare" />
  <AppShell v-else />
  <AppToast />
</template>
