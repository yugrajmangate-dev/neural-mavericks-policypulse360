import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  base: '/neural-mavericks-policypulse360/',
  plugins: [react()],
  build: { chunkSizeWarningLimit: 2000 },
})
