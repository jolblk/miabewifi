import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8001',
      '/routers': 'http://localhost:8001',
      '/wallet': 'http://localhost:8001',
      '/packs': 'http://localhost:8001',
      '/admin': 'http://localhost:8001',
      '/support': 'http://localhost:8001',
      '/notifications': 'http://localhost:8001',
    }
  },
  build: {
    outDir: '../app/static/dist',
    emptyOutDir: true,
  }
})
