import { reactive } from 'vue'

export const toasts = reactive([])

export function toast(message, type = 'info') {
  const id = Date.now() + Math.random()
  toasts.push({ id, message, type })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, 4000)
}

export function applyBrand(settings) {
  if (!settings) return
  const r = document.documentElement
  if (settings.primary_color) r.style.setProperty('--brand-color', settings.primary_color)
  if (settings.page_bg) r.style.setProperty('--page-bg', settings.page_bg)
  if (settings.header_text_color) r.style.setProperty('--header-text', settings.header_text_color)
}
