<template>
  <div class="min-h-screen">
    <CampaignHeader :campaign="campaign" :settings="settings" />
    <main class="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
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

        <div v-if="campaign.description" class="prose prose-sm max-w-none text-gray-700" v-html="campaign.description"></div>

        <div>
          <h2 class="text-lg font-semibold text-gray-900 mb-3">
            {{ campaign.status === 'Voting Open' ? 'Pick an award to vote in' : 'Awards' }}
          </h2>
          <div v-if="!awards.length" class="bg-white border border-dashed border-gray-200 rounded-xl p-10 text-center text-sm text-gray-500">
            No awards in this campaign yet.
          </div>
          <div v-else class="grid gap-3 sm:grid-cols-2">
            <router-link
              v-for="a in awards"
              :key="a.slug"
              :to="{ name: 'vote-award', params: { slug, awardSlug: a.slug } }"
              class="group text-left bg-white border border-gray-200 rounded-xl p-4 hover:border-brand hover:shadow-md transition focus:outline-none focus:ring-2 focus:ring-brand"
              :class="{ 'border-yellow-300 ring-1 ring-yellow-200': a.winner_nomination }"
            >
              <div class="flex items-start gap-3">
                <div class="flex-shrink-0">
                  <Avatar
                    :image="a.icon_or_image"
                    :label="a.award_name"
                    size="2xl"
                    shape="square"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="flex items-start gap-2 flex-wrap">
                    <div class="font-semibold text-gray-900 group-hover:text-brand transition leading-snug break-words min-w-0 flex-1">{{ a.award_name }}</div>
                    <WinnerBadge v-if="a.winner_nomination" class="flex-shrink-0 mt-0.5" />
                  </div>
                  <div class="text-sm text-gray-500 mt-1 line-clamp-2 break-words" v-if="stripHtml(a.description)">{{ stripHtml(a.description) }}</div>
                  <div class="flex items-center gap-3 text-xs text-gray-500 mt-2 flex-wrap">
                    <span class="inline-flex items-center gap-1">
                      <FeatherIcon name="users" class="h-3.5 w-3.5" />
                      {{ (a.finalists || []).length }} {{ (a.finalists || []).length === 1 ? 'finalist' : 'finalists' }}
                    </span>
                    <span v-if="awardVotes(a) > 0" class="inline-flex items-center gap-1">
                      <FeatherIcon name="bar-chart-2" class="h-3.5 w-3.5" />
                      <span class="font-medium text-gray-700">{{ awardVotes(a) }}</span> votes
                    </span>
                  </div>
                </div>
                <FeatherIcon name="arrow-right" class="h-4 w-4 text-gray-400 group-hover:text-brand mt-1 flex-shrink-0 hidden sm:block" />
              </div>
            </router-link>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import CampaignHeader from '../components/CampaignHeader.vue'
import CountdownTimer from '../components/CountdownTimer.vue'
import WinnerBadge from '../components/WinnerBadge.vue'
import api from '../api.js'
import { applyBrand, toast } from '../store.js'

const props = defineProps({ slug: String })

const loading = ref(true)
const campaign = ref(null)
const awards = ref([])
const settings = ref(null)
let timer = null

const stateMessage = computed(() => {
  const s = campaign.value?.status
  if (s === 'Nominations Open') return "Voting hasn't started yet."
  if (s === 'Shortlisting') return 'Voting starts soon — our team is selecting finalists.'
  return 'Not available.'
})

function stripHtml(raw) {
  if (!raw) return ''
  const tmp = document.createElement('div')
  tmp.innerHTML = raw
  return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim()
}

function awardVotes(a) {
  return (a.finalists || []).reduce((s, f) => s + (f.vote_count || 0), 0)
}

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

onMounted(async () => {
  await load()
  timer = setInterval(() => {
    if (campaign.value?.status === 'Voting Open') load()
    else if (campaign.value?.status === 'Closed') clearInterval(timer)
  }, 10000)
})
onUnmounted(() => clearInterval(timer))
</script>

