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
        // Admin API -> admin-agent (8002)
        '/api/admin': {
          target: 'http://localhost:8002',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api\/admin/, '/api'),
        },
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
        }
      }
    }
  }
})
