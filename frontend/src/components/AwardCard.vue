<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5 sm:p-6 shadow-sm">
    <div class="flex items-start gap-4 mb-5">
      <img
        v-if="award.icon_or_image"
        :src="award.icon_or_image"
        :alt="award.award_name"
        class="flex-shrink-0 rounded-lg"
      />
      <div class="flex-1 min-w-0">
        <h2 class="text-base sm:text-lg font-semibold text-gray-900">{{ award.award_name }}</h2>
        <p class="text-sm text-gray-600 mt-1" v-if="award.description">{{ award.description }}</p>
      </div>
      <div class="flex flex-col items-end gap-1.5 flex-shrink-0">
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
    <div v-else class="grid gap-3 md:grid-cols-2">
      <NomineeCard
        v-for="f in award.finalists"
        :key="f.name"
        :finalist="f"
        :can-vote="canVote"
        :show-results="showResults"
        :is-winner="award.winner_nomination === f.name"
        @vote="$emit('vote', { award, finalist: f })"
      />
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import NomineeCard from './NomineeCard.vue'
const props = defineProps({
  award: { type: Object, required: true },
  canVote: { type: Boolean, default: false },
  showResults: { type: Boolean, default: true },
})
defineEmits(['vote'])
const totalVotes = computed(() =>
  (props.award.finalists || []).reduce((s, f) => s + (f.vote_count || 0), 0)
)
</script>
