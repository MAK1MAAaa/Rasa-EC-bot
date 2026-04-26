import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const devHost = String(env.VITE_DEV_HOST || '0.0.0.0').trim() || '0.0.0.0'
  const devPort = Number.parseInt(String(env.VITE_DEV_PORT || '5173'), 10)
  const backendProxyTarget = String(env.VITE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8000').trim()

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: devHost,
      port: Number.isFinite(devPort) ? devPort : 5173,
      proxy: {
        '/api': {
          target: backendProxyTarget,
          changeOrigin: true,
        },
        '/ws': {
          target: backendProxyTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
  }
})
