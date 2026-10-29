import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 开发期 dev server 5173，代理 /api 到后端 9959（docs/08 §2.2）
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:9959',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 生产由后端同源托管，产物落到 server 的静态目录（docs/03 §9）
    outDir: '../server/app/web',
    emptyOutDir: true,
  },
})
