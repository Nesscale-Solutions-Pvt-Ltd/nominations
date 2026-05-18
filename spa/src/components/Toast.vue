<template>
  <div class="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 space-y-2">
    <div
      v-for="t in toasts"
      :key="t.id"
      class="px-4 py-2 rounded-lg shadow-lg text-sm text-white"
      :class="{ 'bg-green-600': t.type === 'success', 'bg-red-600': t.type === 'error', 'bg-gray-800': t.type === 'info' }"
    >
      {{ t.message }}
    </div>
  </div>
</template>

<script setup>
import { toasts } from '../store.js'
</script>
