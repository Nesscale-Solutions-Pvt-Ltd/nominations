<template>
  <Dialog
    v-model="dialogModel"
    :options="{ title: 'Nominee details', size: 'lg' }"
  >
    <template #body-content>
      <div v-if="!finalist" class="text-sm text-gray-500 py-6 text-center">Loading…</div>
      <div v-else class="space-y-4">
        <div class="flex gap-4 items-start">
          <img
            v-if="finalist.nominee_photo"
            :src="finalist.nominee_photo"
            :alt="finalist.nominee_name"
            class="w-24 h-24 object-cover rounded-lg border border-gray-200 cursor-zoom-in hover:opacity-90 transition"
            title="Click to view full image"
            @click="openLightbox(finalist.nominee_photo, finalist.nominee_name)"
          />
          <div
            v-else
            class="w-24 h-24 flex items-center justify-center rounded-lg bg-gray-100 text-gray-500 font-semibold text-2xl select-none"
          >
            {{ finalist.nominee_name?.[0]?.toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <h2 class="text-lg font-semibold text-gray-900">{{ finalist.nominee_name }}</h2>
            <p
              v-if="finalist.designation || finalist.organization"
              class="text-sm mt-0.5"
            >
              <span v-if="finalist.designation" class="font-medium text-teal-700">{{ finalist.designation }}</span>
              <span v-if="finalist.designation && finalist.organization" class="text-gray-400 mx-1.5">•</span>
              <span v-if="finalist.organization" class="text-gray-500">{{ finalist.organization }}</span>
            </p>
            <p class="text-sm text-gray-500" v-if="award">{{ award.award_name }}</p>
            <p class="text-xs text-gray-500 mt-1">
              <span class="font-semibold text-gray-700">{{ finalist.vote_count || 0 }}</span> votes
            </p>
          </div>
        </div>
        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">Why they're nominated</h3>
          <div
            class="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none nominee-justification"
            v-html="finalist.justification"
            @click="onJustificationClick"
          ></div>
        </div>
      </div>
    </template>
    <template #actions>
      <div class="flex gap-2 justify-end">
        <Button @click="close">Close</Button>
        <Button
          v-if="canVote && finalist"
          variant="solid"
          theme="gray"
          class="!bg-brand hover:!opacity-90"
          @click="onVote"
        >
          <template #prefix><FeatherIcon name="check-circle" class="h-4 w-4" /></template>
          Vote for {{ finalist.nominee_name }}
        </Button>
      </div>
    </template>
  </Dialog>
  <ImageLightbox
    :open="lightboxOpen"
    :src="lightboxSrc"
    :alt="lightboxAlt"
    @close="lightboxOpen = false"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import api from '../api.js'
import { toast } from '../store.js'
import ImageLightbox from './ImageLightbox.vue'

const props = defineProps({
  open: Boolean,
  nominationId: String,
  canVote: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'vote'])

const dialogModel = computed({
  get: () => props.open,
  set: (v) => { if (!v) close() },
})
const finalist = ref(null)
const award = ref(null)

watch(() => [props.open, props.nominationId], async ([open, id]) => {
  if (!open || !id) { finalist.value = null; award.value = null; return }
  try {
    const r = await api.getNominee(id)
    finalist.value = r.finalist
    award.value = r.award
  } catch (e) { toast(e.message, 'error'); close() }
})

function close() { emit('close') }
function onVote() { emit('vote', { award: award.value, finalist: finalist.value }) }

const lightboxOpen = ref(false)
const lightboxSrc = ref('')
const lightboxAlt = ref('')
function openLightbox(src, alt) {
  if (!src) return
  lightboxSrc.value = src
  lightboxAlt.value = alt || ''
  lightboxOpen.value = true
}
function onJustificationClick(e) {
  const t = e.target
  if (t && t.tagName === 'IMG' && t.src) {
    e.preventDefault()
    openLightbox(t.src, t.alt || finalist.value?.nominee_name || '')
  }
}
</script>

<style scoped>
.nominee-justification :deep(img) {
  cursor: zoom-in;
  transition: opacity 0.15s ease;
}
.nominee-justification :deep(img:hover) {
  opacity: 0.9;
}
</style>
