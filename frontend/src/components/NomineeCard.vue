<template>
  <div
    class="relative border rounded-lg p-4 sm:p-5 bg-white flex gap-4 transition hover:shadow-md"
    :class="isWinner ? 'border-yellow-300 ring-1 ring-yellow-200' : 'border-gray-200'"
  >
    <img
      v-if="finalist.nominee_photo"
      :src="finalist.nominee_photo"
      :alt="finalist.nominee_name"
      class="flex-shrink-0 rounded-lg w-16 h-16 sm:w-20 sm:h-20 object-cover bg-gray-50 cursor-zoom-in hover:opacity-90 transition"
      title="Click to view full image"
      @click="lightboxOpen = true"
    />
    <div
      v-else
      class="flex-shrink-0 flex items-center justify-center rounded-lg bg-gray-100 text-gray-500 font-semibold text-lg select-none w-16 h-16 sm:w-20 sm:h-20"
    >
      {{ finalist.nominee_name?.[0]?.toUpperCase() }}
    </div>
    <ImageLightbox
      v-if="finalist.nominee_photo"
      :open="lightboxOpen"
      :src="finalist.nominee_photo"
      :alt="finalist.nominee_name"
      @close="lightboxOpen = false"
    />
    <div class="flex-1 min-w-0">
      <div class="flex items-start gap-2 flex-wrap">
        <h3 class="font-semibold text-gray-900 text-sm sm:text-base leading-snug break-words min-w-0 flex-1">{{ finalist.nominee_name }}</h3>
        <WinnerBadge v-if="isWinner" class="flex-shrink-0" />
      </div>
      <p
        v-if="finalist.designation || finalist.organization"
        class="text-xs sm:text-sm text-gray-600 mt-0.5 break-words"
      >
        <span v-if="finalist.designation" class="font-medium text-teal-700">{{ finalist.designation }}</span>
        <span v-if="finalist.designation && finalist.organization" class="text-gray-400 mx-1.5">•</span>
        <span v-if="finalist.organization" class="text-gray-500">{{ finalist.organization }}</span>
      </p>
      <div class="mt-4" v-if="showResults && finalist.vote_count > 0">
        <ResultsBar :count="finalist.vote_count" :percentage="finalist.vote_percentage" />
      </div>
      <div class="mt-4 grid grid-cols-2 gap-2" v-if="canVote">
        <Button variant="subtle" theme="gray" class="w-full justify-center" @click="$emit('details', finalist)">
          <template #prefix><FeatherIcon name="info" class="h-4 w-4" /></template>
          Details
        </Button>
        <Button variant="solid" class="w-full justify-center !bg-brand !text-white !border-transparent hover:!opacity-90" @click="$emit('vote', finalist)">
          <template #prefix><FeatherIcon name="check-circle" class="h-4 w-4" /></template>
          Vote
        </Button>
      </div>
      <div class="mt-4" v-else>
        <Button variant="subtle" theme="gray" class="w-full justify-center" @click="$emit('details', finalist)">
          <template #prefix><FeatherIcon name="info" class="h-4 w-4" /></template>
          View details
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ResultsBar from './ResultsBar.vue'
import WinnerBadge from './WinnerBadge.vue'
import ImageLightbox from './ImageLightbox.vue'

const lightboxOpen = ref(false)

defineProps({
  finalist: { type: Object, required: true },
  canVote: { type: Boolean, default: false },
  showResults: { type: Boolean, default: true },
  isWinner: { type: Boolean, default: false },
})
defineEmits(['vote', 'details'])
</script>

