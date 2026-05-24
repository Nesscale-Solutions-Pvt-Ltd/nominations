<template>
  <div
    class="relative border rounded-lg p-4 bg-white flex gap-4 transition hover:shadow-md"
    :class="isWinner ? 'border-yellow-300 ring-1 ring-yellow-200' : 'border-gray-200'"
  >
    <img
      v-if="finalist.nominee_photo"
      :src="finalist.nominee_photo"
      :alt="finalist.nominee_name"
      class="flex-shrink-0 rounded-lg w-16 h-16 sm:w-20 sm:h-20 object-cover bg-gray-50"
    />
    <div
      v-else
      class="flex-shrink-0 flex items-center justify-center rounded-lg bg-gray-100 text-gray-500 font-semibold text-lg select-none w-16 h-16 sm:w-20 sm:h-20"
    >
      {{ finalist.nominee_name?.[0]?.toUpperCase() }}
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 flex-wrap">
        <h3 class="font-semibold text-gray-900 truncate">{{ finalist.nominee_name }}</h3>
        <WinnerBadge v-if="isWinner" />
      </div>
      <div
        class="text-sm text-gray-600 mt-1 prose prose-sm max-w-none line-clamp-2 nominee-card-justification"
        v-html="justificationPreview"
      ></div>
      <div class="mt-3" v-if="showResults">
        <ResultsBar :count="finalist.vote_count" :percentage="finalist.vote_percentage" />
      </div>
      <div class="mt-3 flex gap-2 flex-wrap">
        <Button variant="subtle" theme="gray" @click="$emit('details', finalist)">
          <template #prefix><FeatherIcon name="info" class="h-4 w-4" /></template>
          View details
        </Button>
        <Button v-if="canVote" variant="solid" theme="gray" @click="$emit('vote', finalist)" class="!bg-brand hover:!opacity-90">
          <template #prefix><FeatherIcon name="check-circle" class="h-4 w-4" /></template>
          Vote
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import ResultsBar from './ResultsBar.vue'
import WinnerBadge from './WinnerBadge.vue'

const props = defineProps({
  finalist: { type: Object, required: true },
  canVote: { type: Boolean, default: false },
  showResults: { type: Boolean, default: true },
  isWinner: { type: Boolean, default: false },
})
defineEmits(['vote', 'details'])

// Strip <img>/<video>/<iframe> tags from the preview so cards don't show
// full-sized media; voters see the full content in the details modal.
const justificationPreview = computed(() => {
  const raw = props.finalist?.justification || ''
  if (!raw) return ''
  return raw.replace(/<(img|video|iframe|source|picture)\b[^>]*>(?:[\s\S]*?<\/\1>)?/gi, '')
})
</script>

<style scoped>
.nominee-card-justification :deep(img),
.nominee-card-justification :deep(video),
.nominee-card-justification :deep(iframe) {
  display: none;
}
</style>
