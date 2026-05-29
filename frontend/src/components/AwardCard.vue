<template>
  <section class="bg-white border border-gray-200 rounded-xl p-4 sm:p-6 shadow-sm">
    <div class="flex items-start gap-3 sm:gap-4 mb-5 flex-wrap sm:flex-nowrap">
      <img
        v-if="award.icon_or_image"
        :src="award.icon_or_image"
        :alt="award.award_name"
        class="flex-shrink-0 rounded-lg w-12 h-12 sm:w-16 sm:h-16 object-cover bg-gray-50"
      />
      <div class="flex-1 min-w-0">
        <h2 class="text-base sm:text-lg font-semibold text-gray-900 leading-snug break-words">{{ award.award_name }}</h2>
        <p
          v-if="descriptionText"
          class="text-sm text-gray-600 mt-1 line-clamp-2 break-words"
        >{{ descriptionText }}</p>
        <div class="flex items-center gap-2 mt-2 sm:hidden flex-wrap">
          <Badge
            v-if="award.finalists?.length"
            :label="`${award.finalists.length} ${award.finalists.length === 1 ? 'finalist' : 'finalists'}`"
            theme="gray"
            variant="subtle"
          />
          <span v-if="totalVotes > 0" class="text-xs text-gray-500 whitespace-nowrap">
            <span class="font-semibold text-gray-700">{{ totalVotes }}</span> votes
          </span>
        </div>
      </div>
      <div class="hidden sm:flex flex-col items-end gap-1.5 flex-shrink-0">
        <Badge
          v-if="award.finalists?.length"
          :label="`${award.finalists.length} ${award.finalists.length === 1 ? 'finalist' : 'finalists'}`"
          theme="gray"
          variant="subtle"
        />
        <span v-if="totalVotes > 0" class="text-xs text-gray-500 whitespace-nowrap">
          <span class="font-semibold text-gray-700">{{ totalVotes }}</span> votes
        </span>
      </div>
    </div>
    <div
      v-if="!award.finalists?.length"
      class="text-sm text-gray-500 py-10 text-center border border-dashed border-gray-200 rounded-lg"
    >
      Finalists will be announced soon.
    </div>
    <template v-else>
      <div
        v-if="votingClosed && !winnerFinalist"
        class="mb-5 rounded-xl border-2 border-dashed border-amber-300 bg-gradient-to-br from-amber-50 to-white p-6 sm:p-8 text-center"
      >
        <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-amber-100 mb-3">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-6 h-6 text-amber-600"><path d="M10 1.5l2.6 5.27 5.82.85-4.21 4.1.99 5.78L10 14.77l-5.2 2.73.99-5.78-4.21-4.1 5.82-.85L10 1.5z"/></svg>
        </div>
        <h3 class="text-base sm:text-lg font-semibold text-gray-900">Voting has ended</h3>
        <p class="text-sm text-amber-800 mt-1 font-medium">The winner will be announced soon. Stay tuned!</p>
      </div>
      <div
        v-else-if="winnerFinalist"
        class="mb-5 rounded-xl border-2 border-amber-300 bg-gradient-to-br from-amber-50 via-yellow-50 to-white p-4 sm:p-5 shadow-md"
      >
        <div class="flex items-center gap-2 mb-4 flex-wrap">
          <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500 text-white text-xs font-bold uppercase tracking-wide shadow-sm">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5"><path d="M10 1.5l2.6 5.27 5.82.85-4.21 4.1.99 5.78L10 14.77l-5.2 2.73.99-5.78-4.21-4.1 5.82-.85L10 1.5z"/></svg>
            Winner
          </span>
          <span class="text-xs sm:text-sm font-medium text-amber-800">{{ award.award_name }}</span>
        </div>
        <div class="flex gap-4 items-start">
          <img
            v-if="winnerFinalist.nominee_photo"
            :src="winnerFinalist.nominee_photo"
            :alt="winnerFinalist.nominee_name"
            class="w-20 h-20 sm:w-28 sm:h-28 rounded-lg object-cover border-2 border-amber-300 flex-shrink-0 cursor-zoom-in hover:opacity-90 transition shadow-sm"
            title="Click to view full image"
            @click="winnerLightboxOpen = true"
          />
          <div
            v-else
            class="w-20 h-20 sm:w-28 sm:h-28 rounded-lg bg-amber-100 border-2 border-amber-300 flex items-center justify-center text-amber-700 font-bold text-2xl flex-shrink-0"
          >
            {{ winnerFinalist.nominee_name?.[0]?.toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-base sm:text-xl font-bold text-gray-900 leading-snug break-words">{{ winnerFinalist.nominee_name }}</h3>
            <p
              v-if="winnerFinalist.designation || winnerFinalist.organization"
              class="text-xs sm:text-sm mt-1 break-words"
            >
              <span v-if="winnerFinalist.designation" class="font-medium text-teal-700">{{ winnerFinalist.designation }}</span>
              <span v-if="winnerFinalist.designation && winnerFinalist.organization" class="text-gray-400 mx-1.5">•</span>
              <span v-if="winnerFinalist.organization" class="text-gray-500">{{ winnerFinalist.organization }}</span>
            </p>
            <div v-if="winnerFinalist.vote_count > 0" class="text-xs text-amber-800 mt-1.5 font-medium">
              {{ winnerFinalist.vote_count }} {{ winnerFinalist.vote_count === 1 ? 'vote' : 'votes' }}<span v-if="winnerFinalist.vote_percentage"> • {{ winnerFinalist.vote_percentage.toFixed(1) }}%</span>
            </div>
          </div>
        </div>
        <button
          v-if="winnerFinalist.justification"
          type="button"
          class="mt-4 w-full inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-600 text-white text-sm font-semibold shadow-sm transition"
          @click="$emit('details', { award, finalist: winnerFinalist })"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2h-1V9z" clip-rule="evenodd"/></svg>
          View full details
        </button>
      </div>
      <ImageLightbox
        v-if="winnerFinalist"
        :open="winnerLightboxOpen"
        :src="winnerFinalist.nominee_photo"
        :alt="winnerFinalist.nominee_name"
        @close="winnerLightboxOpen = false"
      />
      <div class="grid gap-3 md:grid-cols-2">
        <NomineeCard
          v-for="f in award.finalists"
          :key="f.name"
          :finalist="f"
          :can-vote="canVote"
          :show-results="showResults"
          :is-winner="award.winner_nomination === f.name"
          @vote="$emit('vote', { award, finalist: f })"
          @details="$emit('details', { award, finalist: f })"
        />
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'
import NomineeCard from './NomineeCard.vue'
import ImageLightbox from './ImageLightbox.vue'

const winnerLightboxOpen = ref(false)
const props = defineProps({
  award: { type: Object, required: true },
  canVote: { type: Boolean, default: false },
  showResults: { type: Boolean, default: true },
  votingClosed: { type: Boolean, default: false },
})
defineEmits(['vote', 'details'])
const totalVotes = computed(() =>
  (props.award.finalists || []).reduce((s, f) => s + (f.vote_count || 0), 0)
)
const descriptionText = computed(() => {
  const raw = props.award?.description || ''
  if (!raw) return ''
  // Strip HTML for the card preview; full HTML is shown on the award detail page.
  const tmp = document.createElement('div')
  tmp.innerHTML = raw
  return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim()
})
const winnerFinalist = computed(() => {
  if (!props.award?.winner_nomination) return null
  return (props.award.finalists || []).find(f => f.name === props.award.winner_nomination) || null
})
const winnerJustificationPreview = computed(() => {
  const raw = winnerFinalist.value?.justification || ''
  if (!raw) return ''
  return raw.replace(/<(img|video|iframe|source|picture)\b[^>]*>(?:[\s\S]*?<\/\1>)?/gi, '')
})
</script>

<style scoped>
.award-winner-justification :deep(img),
.award-winner-justification :deep(video),
.award-winner-justification :deep(iframe) {
  display: none;
}
</style>
