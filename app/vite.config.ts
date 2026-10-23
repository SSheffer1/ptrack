import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  // In development the page comes from Vite (port 5173) but data comes from the
  // Python server (port 8000). Forwarding /api makes both look like one site.
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
