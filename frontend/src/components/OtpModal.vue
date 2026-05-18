<template>
  <Dialog v-model="dialogModel" :options="{ title: 'Verify your phone', size: 'md' }">
    <template #body-content>
      <div class="space-y-4">
        <p class="text-sm text-gray-600">
          We sent a verification code to
          <span class="font-semibold text-gray-900">{{ phoneMasked }}</span>
        </p>
        <input
          v-model="code"
          inputmode="numeric"
          maxlength="8"
          class="w-full text-center text-2xl font-semibold tracking-[0.4em] border border-gray-300 rounded-lg px-3 py-3 focus:outline-none focus:ring-2 focus:ring-brand focus:border-brand"
          placeholder="••••••"
          @paste="onPaste"
        />
        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <div class="flex gap-2 justify-end">
        <Button @click="close">Cancel</Button>
        <Button
          variant="solid"
          :loading="busy"
          :disabled="code.length < 4"
          @click="submit"
          class="!bg-brand"
        >
          Verify
        </Button>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import api from '../api.js'

const props = defineProps({
  open: Boolean,
  requestId: String,
  phoneMasked: String,
})
const emit = defineEmits(['close', 'verified'])

const dialogModel = computed({
  get: () => props.open,
  set: (v) => { if (!v) close() },
})
function close() { emit('close') }

const code = ref('')
const error = ref('')
const busy = ref(false)

watch(() => props.open, (v) => {
  if (v) { code.value = ''; error.value = '' }
})

function onPaste(e) {
  const t = (e.clipboardData?.getData('text') || '').replace(/\D/g, '')
  if (t) { e.preventDefault(); code.value = t.slice(0, 8) }
}

async function submit() {
  busy.value = true; error.value = ''
  try {
    const out = await api.verifyOtp({ request_id: props.requestId, otp: code.value })
    emit('verified', out.verification_token)
  } catch (e) {
    error.value = e.message || 'Verification failed.'
  } finally {
    busy.value = false
  }
}
</script>
