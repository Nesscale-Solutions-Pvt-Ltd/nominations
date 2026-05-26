<template>
  <div class="min-h-screen">
    <CampaignHeader :campaign="campaign" :settings="settings" />
    <main class="max-w-5xl mx-auto px-3 sm:px-6 py-6 sm:py-8 space-y-4 sm:space-y-6">
      <div v-if="loading" class="flex items-center justify-center py-20 text-gray-500 gap-2">
        <Spinner class="h-4 w-4" /> Loading…
      </div>
      <div
        v-else-if="!['Voting Open','Closed'].includes(campaign?.status)"
        class="bg-white border border-gray-200 rounded-xl p-10 text-center"
      >
        <FeatherIcon name="clock" class="h-8 w-8 mx-auto text-gray-400 mb-3" />
        <p class="text-gray-700">{{ stateMessage }}</p>
      </div>
      <template v-else>
        <div class="flex items-start sm:items-center justify-between gap-2 bg-white border border-gray-200 rounded-xl px-3 sm:px-4 py-3 flex-wrap sm:flex-nowrap">
          <span class="text-sm font-medium text-gray-700 break-words min-w-0 flex-1">{{ award?.award_name }}</span>
          <CountdownTimer
            v-if="campaign.status === 'Voting Open'"
            :target="campaign.voting_end"
            class="flex-shrink-0"
          />
          <Badge v-else theme="gray" variant="subtle" label="Voting Closed" class="flex-shrink-0" />
        </div>
        <AwardCard
          v-if="award"
          :award="award"
          :can-vote="campaign.status === 'Voting Open'"
          :show-results="true"
          @vote="onVote"
          @details="onDetails"
        />
      </template>
    </main>

    <NomineeDetailsModal
      :open="detailsOpen"
      :nomination-id="detailsId"
      :can-vote="campaign?.status === 'Voting Open'"
      @close="detailsOpen = false"
      @vote="onDetailsVote"
    />

    <VoteModal
      :open="voteOpen"
      :target="voteTarget"
      :campaign-slug="slug"
      via="award"
      :default-country="settings?.default_country_code"
      @close="voteOpen = false"
      @voted="onVoted"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CampaignHeader from '../components/CampaignHeader.vue'
import AwardCard from '../components/AwardCard.vue'
import VoteModal from '../components/VoteModal.vue'
import NomineeDetailsModal from '../components/NomineeDetailsModal.vue'
import CountdownTimer from '../components/CountdownTimer.vue'
import api from '../api.js'
import { applyBrand, toast } from '../store.js'

const props = defineProps({ slug: String, awardSlug: String })

const loading = ref(true)
const campaign = ref(null)
const award = ref(null)
const settings = ref(null)
const voteOpen = ref(false)
const voteTarget = ref(null)
const detailsOpen = ref(false)
const detailsId = ref('')
let timer = null

const stateMessage = computed(() => {
  const s = campaign.value?.status
  if (s === 'Nominations Open') return "Voting hasn't started yet."
  if (s === 'Shortlisting') return 'Voting starts soon.'
  return 'Not available.'
})

async function load() {
  try {
    const r = await api.getAward(props.slug, props.awardSlug)
    campaign.value = r.campaign
    award.value = r.award
    settings.value = r.settings
    applyBrand(r.settings)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

function onVote(payload) { voteTarget.value = payload; voteOpen.value = true }
function onVoted() { voteOpen.value = false; load() }
function onDetails(payload) { detailsId.value = payload.finalist?.name; detailsOpen.value = true }
function onDetailsVote(payload) { detailsOpen.value = false; onVote(payload) }

onMounted(async () => {
  await load()
  timer = setInterval(() => {
    if (campaign.value?.status === 'Voting Open') load()
    else if (campaign.value?.status === 'Closed') clearInterval(timer)
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>
