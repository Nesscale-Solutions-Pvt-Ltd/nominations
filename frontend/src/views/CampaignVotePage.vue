<template>
  <div class="min-h-screen">
    <CampaignHeader :campaign="campaign" :settings="settings" />
    <main class="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      <div v-if="loading" class="flex items-center justify-center py-20 text-gray-500 gap-2">
        <Spinner class="h-4 w-4" /> Loading…
      </div>
      <div
        v-else-if="!['Voting Open','Closed'].includes(campaign?.status)"
        class="bg-white border border-gray-200 rounded-xl p-10 text-center"
      >
        <FeatherIcon name="clock" class="h-8 w-8 mx-auto text-gray-400 mb-3" />
        <p class="text-gray-700 text-base">{{ stateMessage }}</p>
      </div>
      <template v-else>
        <div class="flex items-center justify-between bg-white border border-gray-200 rounded-xl px-4 py-3">
          <div class="flex items-center gap-2 text-sm text-gray-700">
            <FeatherIcon name="bar-chart-2" class="h-4 w-4 text-gray-500" />
            <span class="font-medium">{{ campaign.total_votes || 0 }}</span>
            <span class="text-gray-500">total votes</span>
          </div>
          <CountdownTimer
            v-if="campaign.status === 'Voting Open'"
            :target="campaign.voting_end"
          />
          <Badge v-else theme="gray" variant="subtle" label="Voting Closed" />
        </div>
        <AwardCard
          v-for="a in awards"
          :key="a.slug"
          :award="a"
          :can-vote="campaign.status === 'Voting Open'"
          :show-results="true"
          @vote="onVote"
        />
      </template>
    </main>

    <VoteModal
      :open="voteOpen"
      :target="voteTarget"
      :campaign-slug="slug"
      via="campaign"
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
import CountdownTimer from '../components/CountdownTimer.vue'
import api from '../api.js'
import { applyBrand, toast } from '../store.js'

const props = defineProps({ slug: String })

const loading = ref(true)
const campaign = ref(null)
const awards = ref([])
const settings = ref(null)
const voteOpen = ref(false)
const voteTarget = ref(null)
let timer = null

const stateMessage = computed(() => {
  const s = campaign.value?.status
  if (s === 'Nominations Open') return "Voting hasn't started yet."
  if (s === 'Shortlisting') return 'Voting starts soon — our team is selecting finalists.'
  return 'Not available.'
})

async function load() {
  try {
    const r = await api.getCampaign(props.slug)
    campaign.value = r.campaign
    awards.value = r.awards
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

onMounted(async () => {
  await load()
  timer = setInterval(() => {
    if (campaign.value?.status === 'Voting Open') load()
    else if (campaign.value?.status === 'Closed') clearInterval(timer)
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>
