<template>
  <Dialog v-model="dialogModel" :options="{ title: 'Nominate', size: 'lg' }">
    <template #body-content>
      <div class="space-y-4">
        <FormControl
          v-if="!presetAward"
          type="select"
          label="Award"
          v-model="awardSlug"
          :options="awardOptions"
        />
        <FormControl
          type="text"
          label="Nominee name"
          v-model="nomineeName"
          placeholder="Full name"
        />
        <FormControl
          type="textarea"
          label="Why are you nominating them? (min 20 characters)"
          v-model="justification"
          :input-attr="{ rows: 4 }"
        />
        <div>
          <label class="block text-xs text-gray-600 mb-1.5">Photo (optional)</label>
          <input
            type="file"
            accept="image/*"
            @change="onFile"
            class="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-gray-100 file:text-gray-800 hover:file:bg-gray-200"
          />
          <p v-if="uploading" class="text-xs text-gray-500 mt-1 flex items-center gap-1">
            <Spinner class="h-3 w-3" /> Uploading…
          </p>
          <p v-else-if="photoUrl" class="text-xs text-green-700 mt-1 flex items-center gap-1">
            <FeatherIcon name="check-circle" class="h-3 w-3" /> Uploaded
          </p>
        </div>
        <div>
          <label class="block text-xs text-gray-600 mb-1.5">Your phone (for verification)</label>
          <PhoneInput v-model="phone" :default-country="defaultCountry" />
        </div>
        <input type="text" v-model="hp" class="hidden" tabindex="-1" autocomplete="off" />
        <ErrorMessage :message="error" />
      </div>
    </template>
    <template #actions>
      <div class="flex gap-2 justify-end">
        <Button @click="close">Cancel</Button>
        <Button
          variant="solid"
          :loading="busy"
          :disabled="!canSubmit"
          @click="next"
          class="!bg-brand"
        >
          Continue
        </Button>
      </div>
    </template>
  </Dialog>

  <OtpModal
    :open="otpOpen"
    :request-id="otpId"
    :phone-masked="phoneMasked"
    @close="otpOpen = false"
    @verified="onVerified"
  />
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import PhoneInput from './PhoneInput.vue'
import OtpModal from './OtpModal.vue'
import api from '../api.js'
import { toast } from '../store.js'

const props = defineProps({
  open: Boolean,
  awards: { type: Array, default: () => [] },
  presetAward: { type: String, default: null },
  campaignSlug: String,
  defaultCountry: String,
})
const emit = defineEmits(['close', 'submitted', 'update:open'])

const dialogModel = computed({
  get: () => props.open,
  set: (v) => { if (!v) close() },
})
function close() { emit('close') }

const awardSlug = ref(props.presetAward || '')
const nomineeName = ref('')
const justification = ref('')
const phone = ref('')
const hp = ref('')
const photoUrl = ref('')
const uploading = ref(false)
const error = ref('')
const busy = ref(false)
const openedAt = ref(Date.now())

const otpOpen = ref(false)
const otpId = ref('')
const phoneMasked = ref('')

const awardOptions = computed(() => [
  { label: 'Pick an award…', value: '' },
  ...props.awards.map((a) => ({ label: a.award_name, value: a.slug })),
])

const canSubmit = computed(() =>
  (props.presetAward || awardSlug.value) &&
  nomineeName.value.trim() &&
  justification.value.trim().length >= 20 &&
  phone.value
)

watch(() => props.open, (v) => {
  if (v) {
    awardSlug.value = props.presetAward || ''
    nomineeName.value = ''
    justification.value = ''
    phone.value = ''
    photoUrl.value = ''
    error.value = ''
    openedAt.value = Date.now()
  }
})

async function onFile(e) {
  const f = e.target.files?.[0]; if (!f) return
  uploading.value = true
  try {
    const r = await api.uploadFile(f)
    photoUrl.value = r.file_url
  } catch (err) {
    toast(err?.message || 'Upload failed', 'error')
    e.target.value = ''
  }
  uploading.value = false
}

async function next() {
  error.value = ''; busy.value = true
  try {
    const slug = props.presetAward || awardSlug.value
    const r = await api.requestOtp({
      phone: phone.value,
      purpose: 'nominate',
      campaign_slug: props.campaignSlug,
      award_slug: slug,
    })
    if (r.otp_enabled === false && r.verification_token) {
      await onVerified(r.verification_token)
    } else {
      otpId.value = r.request_id
      phoneMasked.value = r.phone_masked
      otpOpen.value = true
    }
  } catch (e) { error.value = e.message }
  busy.value = false
}

async function onVerified(token) {
  try {
    const r = await api.submitNomination({
      verification_token: token,
      award_slug: props.presetAward || awardSlug.value,
      nominee_name: nomineeName.value,
      justification: justification.value,
      nominee_photo_url: photoUrl.value || '',
      hp_field: hp.value,
      open_ms: String(Date.now() - openedAt.value),
    })
    otpOpen.value = false
    emit('submitted', r)
    close()
    toast(r.thank_you_message || 'Submitted', 'success')
  } catch (e) { toast(e.message, 'error') }
}
</script>
