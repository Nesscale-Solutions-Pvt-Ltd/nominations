<template>
  <div class="min-h-screen">
    <CampaignHeader :campaign="campaign" :settings="settings" />
    <main class="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div v-if="loading" class="flex items-center justify-center py-20 text-gray-500 gap-2">
        <Spinner class="h-4 w-4" /> Loading…
      </div>
      <div
        v-else-if="campaign?.status !== 'Nominations Open'"
        class="bg-white border border-gray-200 rounded-xl p-10 text-center"
      >
        <FeatherIcon name="info" class="h-8 w-8 mx-auto text-gray-400 mb-3" />
        <p class="text-gray-700 text-base">{{ stateMessage }}</p>
      </div>
      <div v-else class="space-y-6">
        <div v-if="campaign.description" class="prose prose-sm max-w-none text-gray-700" v-html="campaign.description"></div>
        <div>
          <h2 class="text-lg font-semibold text-gray-900 mb-3">Pick an award to nominate for</h2>
          <div class="grid gap-3 sm:grid-cols-2">
            <router-link
              v-for="a in awards"
              :key="a.slug"
              :to="{ name: 'nominate-award', params: { slug, awardSlug: a.slug } }"
              class="group text-left bg-white border border-gray-200 rounded-xl p-4 hover:border-brand hover:shadow-md transition focus:outline-none focus:ring-2 focus:ring-brand"
            >
              <div class="flex items-start gap-3">
                <Avatar
                  :image="a.icon_or_image"
                  :label="a.award_name"
                  size="2xl"
                  shape="square"
                />
                <div class="flex-1 min-w-0">
                  <div class="font-semibold text-gray-900 group-hover:text-brand transition">{{ a.award_name }}</div>
                  <div class="text-sm text-gray-500 mt-0.5 line-clamp-2" v-if="stripHtml(a.description)">{{ stripHtml(a.description) }}</div>
                </div>
                <FeatherIcon name="arrow-right" class="h-4 w-4 text-gray-400 group-hover:text-brand mt-1" />
              </div>
            </router-link>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import CampaignHeader from '../components/CampaignHeader.vue'
import api from '../api.js'
import { applyBrand, toast } from '../store.js'

const props = defineProps({ slug: String })

const loading = ref(true)
const campaign = ref(null)
const awards = ref([])
const settings = ref(null)

function stripHtml(raw) {
  if (!raw) return ''
  const tmp = document.createElement('div')
  tmp.innerHTML = raw
  return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim()
}

const stateMessage = computed(() => {
  const s = campaign.value?.status
  if (s === 'Shortlisting') return 'Nominations closed — our team is selecting finalists.'
  if (s === 'Voting Open') return 'Nominations are closed. Visit the voting page to cast your vote.'
  if (s === 'Closed') return 'This campaign has ended.'
  return 'Not available.'
})

async function load() {
  loading.value = true
  try {
    const r = await api.getCampaign(props.slug)
    campaign.value = r.campaign
    awards.value = r.awards
    settings.value = r.settings
    applyBrand(r.settings)
  } catch (e) {
    toast(e.message, 'error')
  }
  loading.value = false
}

onMounted(load)
</script>
