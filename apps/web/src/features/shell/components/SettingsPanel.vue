<script setup lang="ts">
// 系统设置类页面的公共外壳：分组卡片容器。
// 页面标题统一由侧栏与浏览器标题交代，页面内不再重复一层大标题（docs/02 §10 组件角色）。
</script>

<template>
  <div class="panel">
    <slot />
  </div>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: var(--space5);
  /* 内容区宽度与内边距由 AppShell 统一处理，页面只排自己的垂直节奏 */
  padding: 0;
}
</style>
