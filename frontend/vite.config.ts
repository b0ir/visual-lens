import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath } from 'node:url'

// Read env files from the repo root so a single root .env serves both the
// frontend and the backend. Only VITE_-prefixed vars are exposed to the client.
const repoRoot = fileURLToPath(new URL('..', import.meta.url))

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  envDir: repoRoot,
})
