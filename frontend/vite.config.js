import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/brainx/',
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ['dev.internal.kronosx.ai'],
    proxy: {
      '/brainx/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/brainx/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
