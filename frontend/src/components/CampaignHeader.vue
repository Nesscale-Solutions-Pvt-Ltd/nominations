<template>
  <header class="border-b border-gray-200" :style="headerStyle">
    <div class="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
      <img
        v-if="settings?.logo"
        :src="settings.logo"
        :alt="settings?.brand_name || 'Logo'"
        class="flex-shrink-0 rounded-lg"
      />
      <div
        v-else
        class="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 text-gray-600 font-semibold text-sm select-none"
      >
        {{ (settings?.brand_name || 'N').slice(0, 1) }}
      </div>
      <div class="flex-1 min-w-0">
        <div class="text-xs uppercase tracking-wider font-medium opacity-70">
          {{ settings?.brand_name || 'Nominations' }}
        </div>
        <h1 class="text-xl sm:text-2xl font-semibold truncate">{{ campaign?.title }}</h1>
      </div>
      <Badge v-if="campaign?.status" :theme="statusTheme" :label="campaign.status" variant="subtle" />
    </div>
    <div v-if="campaign?.cover_image" class="max-w-5xl mx-auto px-4 sm:px-6 pb-4">
      <img :src="campaign.cover_image" class="w-full max-h-56 object-cover rounded-lg border border-gray-200" />
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ campaign: Object, settings: Object })

const headerStyle = computed(() => {
  const s = props.settings
  if (!s) return { backgroundColor: '#ffffff' }
  const primary = s.primary_color || '#1F4E79'
  const style = {}
  if (s.header_gradient_end) {
    const from = s.header_bg || primary
    style.background = `linear-gradient(${s.gradient_direction || 'to right'}, ${from}, ${s.header_gradient_end})`
  } else if (s.header_bg) {
    style.backgroundColor = s.header_bg
  } else {
    style.backgroundColor = '#ffffff'
  }
  if (s.header_text_color) style.color = s.header_text_color
  return style
})

const statusTheme = computed(() => {
  switch (props.campaign?.status) {
    case 'Nominations Open': return 'green'
    case 'Voting Open': return 'blue'
    case 'Shortlisting': return 'orange'
    case 'Closed': return 'gray'
    default: return 'gray'
  }
})
</script>
