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
            class="w-24 h-24 object-cover rounded-lg border border-gray-200"
          />
          <div
            v-else
            class="w-24 h-24 flex items-center justify-center rounded-lg bg-gray-100 text-gray-500 font-semibold text-2xl select-none"
          >
            {{ finalist.nominee_name?.[0]?.toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <h2 class="text-lg font-semibold text-gray-900">{{ finalist.nominee_name }}</h2>
            <p class="text-sm text-gray-500" v-if="award">{{ award.award_name }}</p>
            <p class="text-xs text-gray-500 mt-1">
              <span class="font-semibold text-gray-700">{{ finalist.vote_count || 0 }}</span> votes
            </p>
          </div>
        </div>
        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">Why they're nominated</h3>
          <p class="text-sm text-gray-700 whitespace-pre-line leading-relaxed">{{ finalist.justification }}</p>
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
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import api from '../api.js'
import { toast } from '../store.js'

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
</script>
