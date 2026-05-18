<template>
  <div class="flex gap-2">
    <FormControl
      type="select"
      v-model="cc"
      :options="countryOptions"
      class="w-28"
    />
    <FormControl
      type="text"
      v-model="num"
      placeholder="Mobile number"
      :input-attr="{ inputmode: 'tel', type: 'tel', autocomplete: 'tel' }"
      class="flex-1"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: String,
  defaultCountry: { type: String, default: '+91' },
})
const emit = defineEmits(['update:modelValue'])

const countryOptions = [
  { label: '+91 IN', value: '+91' },
  { label: '+1 US', value: '+1' },
  { label: '+44 UK', value: '+44' },
  { label: '+971 AE', value: '+971' },
  { label: '+61 AU', value: '+61' },
]

const cc = ref(props.defaultCountry || '+91')
const num = ref('')

watch([cc, num], () => {
  const cleaned = (num.value || '').replace(/\D/g, '')
  emit('update:modelValue', cleaned ? `${cc.value}${cleaned}` : '')
})
</script>
