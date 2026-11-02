import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Backend tidak diubah (tanpa CORS): browser hanya bicara ke origin dev server,
    // prefix /api/v1 diteruskan apa adanya. Proxy hanya berlaku di dev server.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
    // Jangan isi allowedHosts: true (celah DNS rebinding). Akses lewat alamat IP sudah diterima bawaan.
  },
})
