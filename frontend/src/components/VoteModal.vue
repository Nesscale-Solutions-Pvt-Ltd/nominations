<template>
  <Dialog v-model="dialogModel" :options="{ title: 'Confirm vote', size: 'md' }">
    <template #body-content>
      <div class="space-y-4">
        <div class="rounded-lg bg-gray-50 border border-gray-200 p-3 text-sm text-gray-700">
          Vote for <span class="font-semibold text-gray-900">{{ target?.finalist?.nominee_name }}</span>
          for <span class="font-semibold text-gray-900">{{ target?.award?.award_name }}</span>?
        </div>
        <FormControl
          type="text"
          label="Business Name"
          v-model="businessName"
          placeholder="Your company / firm"
        />
        <FormControl
          type="text"
          label="Contact Person Name"
          v-model="contactPersonName"
          placeholder="Full name"
        />
        <FormControl
          type="select"
          label="Category"
          v-model="category"
          :options="categoryOptions"
        />
        <div>
          <label class="block text-xs text-gray-600 mb-1.5">Mobile No (one vote per award)</label>
          <PhoneInput v-model="phone" :default-country="defaultCountry" />
        </div>
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
  target: Object,
  campaignSlug: String,
  via: { type: String, default: 'campaign' },
  defaultCountry: String,
})
const emit = defineEmits(['close', 'voted'])

const dialogModel = computed({
  get: () => props.open,
  set: (v) => { if (!v) close() },
})
function close() { emit('close') }

const phone = ref('')
const businessName = ref('')
const contactPersonName = ref('')
const category = ref('')
const busy = ref(false)
const error = ref('')

const categoryOptions = [
  { label: 'Select a category', value: '' },
  { label: 'Farmer', value: 'Farmer' },
  { label: 'Pollen Officer', value: 'Pollen Officer' },
  { label: 'Technician', value: 'Technician' },
  { label: 'Back Office', value: 'Back Office' },
  { label: 'Factory', value: 'Factory' },
  { label: 'Management', value: 'Management' },
]

const otpOpen = ref(false)
const otpId = ref('')
const phoneMasked = ref('')

const canSubmit = computed(() =>
  phone.value &&
  businessName.value.trim() &&
  contactPersonName.value.trim() &&
  category.value
)

watch(() => props.open, (v) => {
  if (v) {
    phone.value = ''
    businessName.value = ''
    contactPersonName.value = ''
    category.value = ''
    error.value = ''
  }
})

async function next() {
  error.value = ''; busy.value = true
  try {
    const r = await api.requestOtp({
      phone: phone.value,
      purpose: 'vote',
      campaign_slug: props.campaignSlug,
      award_slug: props.target?.award?.slug,
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
    const r = await api.submitVote({
      verification_token: token,
      nomination_id: props.target?.finalist?.name,
      business_name: businessName.value,
      contact_person_name: contactPersonName.value,
      category: category.value,
      via: props.via,
    })
    otpOpen.value = false
    emit('voted', r)
    close()
    toast(r.thank_you_message || 'Voted!', 'success')
  } catch (e) { toast(e.message, 'error') }
}
</script>
