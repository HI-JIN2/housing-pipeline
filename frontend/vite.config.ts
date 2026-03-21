import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env from repo root
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  
  // Set variable for index.html replacement
  process.env.VITE_KAKAO_JS_KEY = env.KAKAO_JS_KEY || ''

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        }
      }
    }
  }
})
