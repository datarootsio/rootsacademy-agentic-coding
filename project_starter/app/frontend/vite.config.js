import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The UI never talks to a database. Everything goes through /api, which is
// the application-service seam of spec D42.
export default defineConfig({
  plugins: [react()],
  server: {
    // Bind IPv4 explicitly: on macOS 'localhost' resolves to ::1 first, and the
    // lab's health probe (and most curl invocations) go to 127.0.0.1.
    host: '127.0.0.1',
    port: 5273,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.SAVING_STREAK_API ?? 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
    },
  },
})
