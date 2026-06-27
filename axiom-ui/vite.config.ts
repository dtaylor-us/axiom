/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: process.env.API_PROXY_TARGET || 'http://localhost:8081',
        changeOrigin: true,
      },
      '/specweaver-api': {
        target: process.env.SPECWEAVER_API_PROXY_TARGET || 'http://localhost:8082',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/specweaver-api/, ''),
      },
      '/lens-api': {
        target: process.env.LENS_API_PROXY_TARGET || 'http://localhost:8083',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/lens-api/, ''),
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/main.tsx', 'src/vite-env.d.ts', 'src/types/**'],
      thresholds: { lines: 80 },
    },
  },
})
