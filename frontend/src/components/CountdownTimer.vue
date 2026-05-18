<template>
  <span class="text-xs text-gray-600">{{ display }}</span>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
const props = defineProps({ target: [String, Date], prefix: String })
const now = ref(Date.now())
let t
onMounted(() => { t = setInterval(() => (now.value = Date.now()), 1000) })
onUnmounted(() => clearInterval(t))

const display = computed(() => {
  if (!props.target) return ''
  const target = new Date(props.target).getTime()
  let diff = Math.max(0, Math.floor((target - now.value) / 1000))
  if (diff === 0) return 'ended'
  const d = Math.floor(diff / 86400); diff -= d * 86400
  const h = Math.floor(diff / 3600); diff -= h * 3600
  const m = Math.floor(diff / 60)
  const parts = []
  if (d) parts.push(`${d}d`)
  if (h) parts.push(`${h}h`)
  parts.push(`${m}m`)
  return `${props.prefix || 'closes in'} ${parts.join(' ')}`
})
</script>
