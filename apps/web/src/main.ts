import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from '@/App.vue'
import { setUnauthorizedHandler } from '@/core/api/client'
import { router } from '@/core/router'
import { initTheme } from '@/core/theme'
import '@/core/theme/base.css'

// index.html 已在首帧前写过一次，这里补齐规范化（非法值回退、补 data-accent）
initTheme()

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 刷新失败（refresh 过期 / 重放检测）→ 统一回登录页，可回到原页面
setUnauthorizedHandler(() => {
  const current = router.currentRoute.value
  if (current.name === 'login') return
  void router.replace({ name: 'login', query: { redirect: current.fullPath } })
})

// 等首屏路由解析完成再挂载：避免 bare 页（登录 / 播放）在首帧误套一层外壳，
// 也避免登录页尚未拿到令牌就触发只有壳内才需要的数据请求。
void router.isReady().then(() => app.mount('#app'))
