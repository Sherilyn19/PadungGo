import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Dev only: set PADUNGGO_DEV_PROXY (e.g. to the live API origin) and
// VITE_API_BASE_URL=/api/v1 to test the UI without running the backend.
// The browser then calls the dev server, which forwards /api requests.
const devProxy = process.env.PADUNGGO_DEV_PROXY

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: devProxy ? { proxy: { '/api': { target: devProxy, changeOrigin: true, secure: true } } } : undefined,
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
