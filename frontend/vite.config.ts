// vite.config.ts

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',  // Specify output directory for build artifacts
    emptyOutDir: true,  // Remove old files before building
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  // (Optional) If you use Vitest for unit tests:
  // test: {
  //   environment: 'jsdom',
  //   setupFiles: './src/setupTests.ts',
  //   globals: true
  // },
});