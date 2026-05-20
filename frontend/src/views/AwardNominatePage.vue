<template>
  <div class="min-h-screen bg-gray-50">
    <main class="max-w-4xl mx-auto px-4 sm:px-6 py-8">
      <div v-if="loading" class="flex items-center justify-center py-20 text-gray-500 gap-2">
        <Spinner class="h-4 w-4" /> Loading…
      </div>
      <div
        v-else-if="campaign?.status !== 'Nominations Open'"
        class="bg-white border border-gray-200 rounded-xl p-10 text-center"
      >
        <FeatherIcon name="info" class="h-8 w-8 mx-auto text-gray-400 mb-3" />
        <p class="text-gray-700 text-base">Nominations are not currently open.</p>
      </div>
      <template v-else-if="award">
        <button
          @click="back"
          class="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-brand mb-4"
        >
          <FeatherIcon name="arrow-left" class="h-4 w-4" /> Back to awards
        </button>

        <section class="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div
            v-if="award.icon_or_image"
            class="w-full aspect-[16/9] bg-gray-100 overflow-hidden"
          >
            <img
              :src="award.icon_or_image"
              :alt="award.award_name"
              class="w-full h-full object-cover"
            />
          </div>
          <div class="p-6 sm:p-8 space-y-4">
            <h1 class="text-2xl font-semibold text-gray-900">{{ award.award_name }}</h1>
            <div
              v-if="award.description"
              class="prose prose-sm max-w-none text-gray-700 leading-relaxed"
              v-html="award.description"
            ></div>
            <div class="pt-2">
              <Button
                variant="solid"
                theme="gray"
                @click="modalOpen = true"
                class="!bg-brand hover:!opacity-90"
              >
                <template #prefix><FeatherIcon name="user-plus" class="h-4 w-4" /></template>
                Nominate for this award
              </Button>
            </div>
          </div>
        </section>
      </template>
    </main>

    <NominateModal
      :open="modalOpen"
      :awards="awards"
      :preset-award="awardSlug"
      :campaign-slug="slug"
      :default-country="settings?.default_country_code"
      @close="modalOpen = false"
      @submitted="onSubmitted"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import NominateModal from '../components/NominateModal.vue'
import api from '../api.js'
import { applyBrand, toast } from '../store.js'

const props = defineProps({ slug: String, awardSlug: String })
const router = useRouter()

const loading = ref(true)
const campaign = ref(null)
const award = ref(null)
const awards = ref([])
const settings = ref(null)
const modalOpen = ref(false)

function back() { router.push({ name: 'nominate', params: { slug: props.slug } }) }

async function load() {
  try {
    const r = await api.getAward(props.slug, props.awardSlug)
    campaign.value = r.campaign
    award.value = r.award
    awards.value = [r.award]
    settings.value = r.settings
    applyBrand(r.settings)
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

function onSubmitted() {
  modalOpen.value = false
  toast('Thank you! Your nomination has been received.', 'success')
}

onMounted(load)
</script>
