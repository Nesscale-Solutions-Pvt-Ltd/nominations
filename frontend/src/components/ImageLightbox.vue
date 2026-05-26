<template>
  <Teleport to="body">
    <transition name="fade">
      <div
        v-if="open"
        class="fixed inset-0 z-[9999] bg-black/85 flex items-center justify-center p-4 cursor-zoom-out"
        @click.self="close"
        @keydown.esc.stop="close"
        tabindex="-1"
        ref="overlay"
      >
        <button
          type="button"
          class="absolute top-4 right-4 text-white/90 hover:text-white bg-white/10 hover:bg-white/20 rounded-full p-2 transition"
          aria-label="Close"
          @click="close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
            <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"/>
          </svg>
        </button>
        <img
          v-if="src"
          :src="src"
          :alt="alt || ''"
          class="max-w-[95vw] max-h-[90vh] object-contain rounded-lg shadow-2xl cursor-default"
          @click.stop
        />
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  open: Boolean,
  src: String,
  alt: String,
})
const emit = defineEmits(['close'])

const overlay = ref(null)

function close() { emit('close') }

function onKey(e) {
  if (e.key === 'Escape' && props.open) close()
}

watch(() => props.open, async (v) => {
  if (v) {
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    await nextTick()
    overlay.value?.focus?.()
  } else {
    document.removeEventListener('keydown', onKey)
    document.body.style.overflow = ''
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
