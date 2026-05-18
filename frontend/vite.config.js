import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import frappeui from 'frappe-ui/vite'
import path from 'path'
import fs from 'fs'

// Build into nominations/public/frontend (assets served at /assets/nominations/frontend/),
// then move the generated index.html into nominations/www/nominations.html so Frappe
// serves it as a website page.
const publicDir = path.resolve(__dirname, '../nominations/public/frontend')
const wwwHtml = path.resolve(__dirname, '../nominations/www/nominations.html')

function moveIndexHtmlToWww() {
  return {
    name: 'nominations-move-index-html',
    closeBundle() {
      const src = path.join(publicDir, 'index.html')
      if (fs.existsSync(src)) {
        fs.mkdirSync(path.dirname(wwwHtml), { recursive: true })
        fs.copyFileSync(src, wwwHtml)
        fs.unlinkSync(src)
      }
    },
  }
}

export default defineConfig({
  plugins: [
    frappeui({
      lucideIcons: true,
      frappeProxy: true,
      frappeTypes: false,
      jinjaBootData: false,
      buildConfig: false,
    }),
    vue(),
    moveIndexHtmlToWww(),
  ],
  base: '/assets/nominations/frontend/',
  build: {
    outDir: publicDir,
    emptyOutDir: true,
    sourcemap: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
})
