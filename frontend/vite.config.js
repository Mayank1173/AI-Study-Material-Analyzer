import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// FastAPI dev server that the Vite proxy forwards /api requests to.
const BACKEND = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    // Forward API calls to the FastAPI backend so one origin serves both the
    // UI and /api (required for the single public test link).
    proxy: {
      '/api': { target: BACKEND, changeOrigin: true },
      '/health': { target: BACKEND, changeOrigin: true },
      '/docs': { target: BACKEND, changeOrigin: true },
    },
    // The public test tunnel forwards a different Host header; Vite 6+ blocks
    // those by default.
    allowedHosts: true,
  },
})
