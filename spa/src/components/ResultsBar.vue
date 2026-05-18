<template>
  <div>
    <div class="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
      <div class="results-bar h-full bg-brand" :style="{ width: pct + '%' }"></div>
    </div>
    <div class="text-xs text-gray-600 mt-1.5 flex justify-between">
      <span class="font-medium">{{ count }} {{ count === 1 ? 'vote' : 'votes' }}</span>
      <span>{{ pct.toFixed(1) }}%</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ count: { type: Number, default: 0 }, percentage: { type: Number, default: 0 } })
const pct = computed(() => Math.min(100, Math.max(0, props.percentage || 0)))
const count = computed(() => props.count || 0)
</script>
