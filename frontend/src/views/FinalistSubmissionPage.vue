<template>
  <div class="min-h-screen bg-[var(--page-bg,#f9fafb)]">
    <header class="px-4 sm:px-6 py-6 border-b border-gray-200" :style="headerStyle">
      <div class="max-w-4xl mx-auto flex items-center gap-4">
        <img
          v-if="settings?.logo"
          :src="settings.logo"
          alt="logo"
          class="h-10 w-10 object-contain rounded bg-white/80 p-1"
        />
        <div class="flex-1 min-w-0">
          <div class="text-xs uppercase tracking-wide opacity-80">
            {{ campaign?.title || settings?.brand_name || 'Nominations' }}
          </div>
          <div class="text-lg sm:text-xl font-semibold truncate">
            {{ award?.award_name || 'Finalist Submission' }}
          </div>
        </div>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
      <div
        v-if="loading"
        class="flex items-center justify-center py-20 text-gray-500 gap-2"
      >
        <Spinner class="h-4 w-4" /> Loading…
      </div>

      <div
        v-else-if="error"
        class="bg-white border border-red-200 rounded-xl p-8 text-center"
      >
        <FeatherIcon name="alert-triangle" class="h-8 w-8 mx-auto text-red-400 mb-3" />
        <p class="text-gray-700">{{ error }}</p>
      </div>

      <template v-else-if="finalist">
        <!-- Nominee greeting -->
        <section class="bg-white rounded-xl border border-gray-200 p-5 sm:p-6 mb-6">
          <div class="flex items-start gap-4">
            <img
              v-if="finalist.nominee_photo"
              :src="finalist.nominee_photo"
              :alt="finalist.nominee_name"
              class="h-14 w-14 rounded-full object-cover border"
            />
            <div class="flex-1 min-w-0">
              <div class="text-base sm:text-lg font-semibold text-gray-900">
                Hello, {{ finalist.nominee_name }}
              </div>
              <div
                v-if="finalist.designation || finalist.organization"
                class="text-sm text-gray-600 mt-0.5"
              >
                {{ [finalist.designation, finalist.organization].filter(Boolean).join(' · ') }}
              </div>
            </div>
          </div>

          <div
            v-if="finalist.intro_message"
            class="prose prose-sm max-w-none text-gray-700 mt-4"
            v-html="finalist.intro_message"
          ></div>

          <div
            v-if="finalist.locked"
            class="mt-4 rounded-lg bg-green-50 border border-green-200 text-green-800 text-sm p-3 flex items-start gap-2"
          >
            <FeatherIcon name="check-circle" class="h-4 w-4 mt-0.5 shrink-0" />
            <div>
              <div class="font-medium">You have already submitted your response.</div>
              <div class="text-green-700/80 text-xs mt-0.5">
                Thank you! Your answers are with our team and can no longer be edited.
              </div>
            </div>
          </div>
        </section>

        <!-- Submitted summary (read-only) -->
        <section
          v-if="finalist.locked"
          class="bg-white rounded-xl border border-gray-200 p-5 sm:p-6"
        >
          <h3 class="text-base font-semibold text-gray-900 mb-4">
            Your submitted response
          </h3>
          <div v-if="!criteria.length" class="text-sm text-gray-500">
            No criteria.
          </div>
          <div v-else class="space-y-4">
            <article
              v-for="(c, idx) in criteria"
              :key="c.name"
              class="border border-gray-200 rounded-lg p-4"
            >
              <div class="flex items-center justify-between gap-2">
                <div class="text-sm font-medium text-gray-900">
                  {{ idx + 1 }}. {{ c.criteria_name }}
                </div>
                <span
                  class="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full"
                  :class="isAnswered(c) ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'"
                >
                  {{ isAnswered(c) ? 'Answered' : 'Skipped' }}
                </span>
              </div>
              <div
                v-if="responses[c.name]"
                class="text-sm text-gray-700 mt-2 whitespace-pre-line"
              >{{ responses[c.name] }}</div>
              <div
                v-else
                class="text-xs text-gray-400 italic mt-2"
              >
                No text response.
              </div>

              <div
                v-if="imagesOf(c).length"
                class="grid grid-cols-2 sm:grid-cols-3 gap-2 mt-3"
              >
                <a
                  v-for="f in imagesOf(c)"
                  :key="f.file_url"
                  :href="f.file_url"
                  target="_blank"
                  rel="noopener"
                  class="block rounded-lg overflow-hidden border border-gray-200 aspect-square bg-gray-50"
                >
                  <img :src="f.file_url" :alt="filenameOf(f.file_url)" class="object-cover w-full h-full" />
                </a>
              </div>
              <ul v-if="nonImagesOf(c).length" class="space-y-2 mt-3">
                <li
                  v-for="f in nonImagesOf(c)"
                  :key="f.file_url"
                  class="flex items-center gap-3 rounded-lg border border-gray-200 p-2.5"
                >
                  <FeatherIcon :name="iconFor(f.file_type)" class="h-4 w-4 text-gray-500 shrink-0" />
                  <a
                    :href="f.file_url"
                    target="_blank"
                    rel="noopener"
                    class="flex-1 text-sm text-gray-800 hover:text-brand truncate"
                  >
                    {{ filenameOf(f.file_url) }}
                  </a>
                  <span class="text-xs text-gray-400 hidden sm:inline">{{ f.file_type }}</span>
                </li>
              </ul>
            </article>
          </div>
        </section>

        <!-- Stepper (editable) -->
        <template v-else-if="criteria.length">
          <!-- Step pills (clickable) -->
          <div class="bg-white rounded-xl border border-gray-200 p-3 sm:p-4 mb-4">
            <div class="flex items-center justify-between mb-3">
              <div class="text-xs text-gray-500">
                Step {{ activeStep + 1 }} of {{ criteria.length }}
              </div>
              <div class="text-xs text-gray-500">
                {{ completedCount }} answered · {{ skippedCount }} skipped
              </div>
            </div>

            <div class="flex items-center gap-1 overflow-x-auto pb-1">
              <template v-for="(c, idx) in criteria" :key="c.name">
                <button
                  type="button"
                  class="shrink-0 h-8 min-w-[2rem] px-2 rounded-full text-xs font-medium border transition flex items-center gap-1"
                  :class="pillClass(idx)"
                  :title="c.criteria_name"
                  @click="goTo(idx)"
                >
                  <span
                    class="h-5 w-5 rounded-full flex items-center justify-center text-[10px]"
                    :class="pillDotClass(idx)"
                  >
                    <FeatherIcon
                      v-if="isAnswered(c)"
                      name="check"
                      class="h-3 w-3"
                    />
                    <span v-else>{{ idx + 1 }}</span>
                  </span>
                  <span class="hidden sm:inline max-w-[10rem] truncate">
                    {{ c.criteria_name }}
                  </span>
                </button>
                <div
                  v-if="idx < criteria.length - 1"
                  class="hidden sm:block flex-1 h-px bg-gray-200 mx-0.5"
                ></div>
              </template>
            </div>

            <!-- progress bar -->
            <div class="h-1.5 mt-3 bg-gray-100 rounded-full overflow-hidden">
              <div
                class="h-full bg-brand transition-all"
                :style="{ width: progressPct + '%' }"
              ></div>
            </div>
          </div>

          <!-- Active criterion -->
          <article
            v-if="activeCriteria"
            :key="activeCriteria.name"
            class="bg-white rounded-xl border border-gray-200 p-5 sm:p-6"
          >
            <div class="text-xs uppercase tracking-wide text-gray-500">
              Criteria {{ activeStep + 1 }} of {{ criteria.length }}
            </div>
            <h3 class="text-base sm:text-lg font-semibold text-gray-900 mt-0.5">
              {{ activeCriteria.criteria_name }}
            </h3>
            <p
              v-if="activeCriteria.description"
              class="text-sm text-gray-600 mt-1 whitespace-pre-line"
            >{{ activeCriteria.description }}</p>

            <div class="mt-4">
              <label class="text-sm font-medium text-gray-700">
                Your response
              </label>
              <textarea
                v-model="responses[activeCriteria.name]"
                rows="6"
                :disabled="finalist.locked"
                class="mt-1 block w-full rounded-lg border border-gray-300 focus:border-brand focus:ring-1 focus:ring-brand text-sm p-3"
                placeholder="Share what you've delivered. You can also upload supporting files below, or skip this question."
              ></textarea>
            </div>

            <div class="mt-5">
              <div class="flex items-center justify-between mb-2">
                <div class="text-sm font-medium text-gray-700">
                  Images, videos &amp; documents
                  <span class="text-xs text-gray-500 font-normal">
                    (optional · up to 100 MB each)
                  </span>
                </div>
                <label
                  v-if="!finalist.locked"
                  class="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md bg-gray-100 hover:bg-gray-200 cursor-pointer text-gray-700"
                >
                  <FeatherIcon name="upload" class="h-3.5 w-3.5" />
                  <span v-if="uploading">Uploading…</span>
                  <span v-else>Upload</span>
                  <input
                    type="file"
                    class="hidden"
                    multiple
                    :disabled="uploading"
                    @change="onUpload($event, activeCriteria)"
                  />
                </label>
              </div>

              <div
                v-if="imagesOf(activeCriteria).length"
                class="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-2"
              >
                <div
                  v-for="f in imagesOf(activeCriteria)"
                  :key="f.file_url"
                  class="relative group rounded-lg overflow-hidden border border-gray-200 aspect-square bg-gray-50"
                >
                  <a :href="f.file_url" target="_blank" rel="noopener">
                    <img
                      :src="f.file_url"
                      :alt="filenameOf(f.file_url)"
                      class="object-cover w-full h-full"
                    />
                  </a>
                  <button
                    v-if="!finalist.locked"
                    type="button"
                    class="absolute top-1 right-1 bg-white/90 rounded-full p-1 text-gray-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition"
                    @click="removeFile(activeCriteria, f)"
                  >
                    <FeatherIcon name="x" class="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              <ul class="space-y-2">
                <li
                  v-for="f in nonImagesOf(activeCriteria)"
                  :key="f.file_url"
                  class="flex items-center gap-3 rounded-lg border border-gray-200 p-2.5"
                >
                  <FeatherIcon :name="iconFor(f.file_type)" class="h-4 w-4 text-gray-500 shrink-0" />
                  <a
                    :href="f.file_url"
                    target="_blank"
                    rel="noopener"
                    class="flex-1 text-sm text-gray-800 hover:text-brand truncate"
                  >
                    {{ filenameOf(f.file_url) }}
                  </a>
                  <span class="text-xs text-gray-400 hidden sm:inline">
                    {{ f.file_type }}
                  </span>
                  <button
                    v-if="!finalist.locked"
                    type="button"
                    class="text-gray-400 hover:text-red-500"
                    @click="removeFile(activeCriteria, f)"
                  >
                    <FeatherIcon name="x" class="h-4 w-4" />
                  </button>
                </li>
              </ul>
            </div>

            <!-- Step nav -->
            <div class="mt-6 flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-gray-100">
              <button
                type="button"
                class="px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-40 inline-flex items-center gap-1"
                :disabled="activeStep === 0"
                @click="prev"
              >
                <FeatherIcon name="arrow-left" class="h-4 w-4" />
                Previous
              </button>

              <div class="flex flex-wrap items-center gap-2 ml-auto">
                <button
                  v-if="!isLast && !finalist.locked"
                  type="button"
                  class="px-3 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-50 inline-flex items-center gap-1"
                  @click="skipAndNext"
                >
                  Skip
                  <FeatherIcon name="skip-forward" class="h-4 w-4" />
                </button>
                <button
                  v-if="!isLast"
                  type="button"
                  class="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium hover:opacity-90 inline-flex items-center gap-1"
                  @click="next"
                >
                  Next
                  <FeatherIcon name="arrow-right" class="h-4 w-4" />
                </button>
                <button
                  v-if="isLast && !finalist.locked"
                  type="button"
                  class="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium hover:opacity-90 inline-flex items-center gap-1 disabled:opacity-60"
                  :disabled="saving"
                  @click="confirmSubmit"
                >
                  <Spinner v-if="saving && submittingFinal" class="h-3.5 w-3.5" />
                  Review &amp; submit
                  <FeatherIcon v-if="!saving" name="check" class="h-4 w-4" />
                </button>
              </div>
            </div>
          </article>

          <!-- Save draft (always available, low key) -->
          <div
            v-if="!finalist.locked"
            class="mt-4 flex items-center justify-end"
          >
            <button
              type="button"
              class="text-xs text-gray-500 hover:text-gray-700 underline-offset-2 hover:underline disabled:opacity-50"
              :disabled="saving"
              @click="save(false)"
            >
              <Spinner v-if="saving && !submittingFinal" class="h-3 w-3 inline mr-1" />
              Save progress
            </button>
          </div>
        </template>

        <div
          v-else-if="!finalist.locked"
          class="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-500"
        >
          No criteria configured yet. Please check back later.
        </div>
      </template>
    </main>

    <!-- Review modal -->
    <div
      v-if="reviewOpen"
      class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4"
      @click.self="reviewOpen = false"
    >
      <div class="bg-white w-full sm:max-w-2xl rounded-t-2xl sm:rounded-2xl shadow-xl max-h-[90vh] flex flex-col">
        <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 class="text-base font-semibold text-gray-900">Review your responses</h3>
          <button type="button" class="text-gray-400 hover:text-gray-600" @click="reviewOpen = false">
            <FeatherIcon name="x" class="h-5 w-5" />
          </button>
        </div>
        <div class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <div
            v-for="(c, idx) in criteria"
            :key="c.name"
            class="border border-gray-200 rounded-lg p-3"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="text-sm font-medium text-gray-900">
                {{ idx + 1 }}. {{ c.criteria_name }}
              </div>
              <span
                class="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full"
                :class="isAnswered(c) ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'"
              >
                {{ isAnswered(c) ? 'Answered' : 'Skipped' }}
              </span>
            </div>
            <div
              v-if="responses[c.name]"
              class="text-sm text-gray-700 mt-2 whitespace-pre-line"
            >{{ responses[c.name] }}</div>
            <div
              v-if="c.response_files && c.response_files.length"
              class="text-xs text-gray-500 mt-2"
            >
              {{ c.response_files.length }} file{{ c.response_files.length === 1 ? '' : 's' }} attached
            </div>
            <button
              type="button"
              class="text-xs text-brand hover:underline mt-2"
              @click="goTo(idx); reviewOpen = false"
            >
              Edit
            </button>
          </div>
        </div>
        <div class="px-5 py-4 border-t border-gray-200 flex items-center justify-between gap-3 bg-gray-50 rounded-b-2xl">
          <div v-if="skippedCount" class="text-xs text-amber-700">
            {{ skippedCount }} question{{ skippedCount === 1 ? '' : 's' }} will be submitted as no answer.
          </div>
          <div v-else class="text-xs text-gray-500">
            All questions answered.
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-100"
              @click="reviewOpen = false"
            >
              Keep editing
            </button>
            <button
              type="button"
              class="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium hover:opacity-90 disabled:opacity-60"
              :disabled="saving"
              @click="submitFinal"
            >
              <Spinner v-if="saving && submittingFinal" class="h-3.5 w-3.5 inline mr-1" />
              Submit
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import api from '../api.js'
import { applyBrand, toast } from '../store.js'

const props = defineProps({ token: String })

const loading = ref(true)
const saving = ref(false)
const submittingFinal = ref(false)
const uploading = ref(false)
const error = ref('')
const reviewOpen = ref(false)

const finalist = ref(null)
const campaign = ref(null)
const award = ref(null)
const settings = ref(null)
const criteria = ref([])
const responses = reactive({})
const activeStep = ref(0)

const headerStyle = computed(() => {
  const s = settings.value || {}
  if (s.header_bg && s.header_gradient_end) {
    return {
      background: `linear-gradient(${s.gradient_direction || 'to right'}, ${s.header_bg}, ${s.header_gradient_end})`,
      color: s.header_text_color || '#fff',
    }
  }
  return {
    background: s.header_bg || s.primary_color || '#1F4E79',
    color: s.header_text_color || '#fff',
  }
})

const activeCriteria = computed(() => criteria.value[activeStep.value] || null)
const isLast = computed(() => activeStep.value === criteria.value.length - 1)

function isAnswered(c) {
  const text = (responses[c.name] || '').trim()
  const hasFiles = (c.response_files || []).length > 0
  return !!(text || hasFiles)
}

const completedCount = computed(() => criteria.value.filter(isAnswered).length)
const skippedCount = computed(() => criteria.value.length - completedCount.value)
const progressPct = computed(() => {
  if (!criteria.value.length) return 0
  return Math.round(((activeStep.value + 1) / criteria.value.length) * 100)
})

function pillClass(idx) {
  if (idx === activeStep.value) return 'border-brand text-brand bg-brand/5'
  if (isAnswered(criteria.value[idx])) return 'border-green-200 text-green-700 bg-green-50'
  return 'border-gray-200 text-gray-500 bg-white hover:bg-gray-50'
}
function pillDotClass(idx) {
  if (idx === activeStep.value) return 'bg-brand text-white'
  if (isAnswered(criteria.value[idx])) return 'bg-green-500 text-white'
  return 'bg-gray-200 text-gray-600'
}

function imagesOf(c) {
  return (c.response_files || []).filter((f) => f.file_type === 'Image')
}
function nonImagesOf(c) {
  return (c.response_files || []).filter((f) => f.file_type !== 'Image')
}
function filenameOf(url) {
  if (!url) return ''
  try { return decodeURIComponent(url.split('/').pop().split('?')[0]) }
  catch (_) { return url }
}
function iconFor(type) {
  if (type === 'Image') return 'image'
  if (type === 'Video') return 'film'
  if (type === 'Document') return 'file-text'
  return 'paperclip'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const r = await api.getFinalistSubmission(props.token)
    finalist.value = r.finalist
    campaign.value = r.campaign
    award.value = r.award
    settings.value = r.settings
    criteria.value = r.criteria || []
    for (const c of criteria.value) {
      responses[c.name] = c.response_text || ''
      if (!Array.isArray(c.response_files)) c.response_files = []
    }
    applyBrand(settings.value)
    document.title = `${award.value?.award_name || 'Finalist'} · ${campaign.value?.title || 'Nominations'}`
  } catch (e) {
    error.value = e.message || 'Unable to load submission.'
  } finally {
    loading.value = false
  }
}

function goTo(idx) {
  if (idx < 0 || idx >= criteria.value.length) return
  activeStep.value = idx
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
function prev() { goTo(activeStep.value - 1) }
function next() {
  // Autosave silently before moving on so progress isn't lost.
  save(false, { silent: true })
  goTo(activeStep.value + 1)
}
function skipAndNext() {
  responses[activeCriteria.value.name] = ''
  next()
}

async function save(submit, { silent = false } = {}) {
  if (saving.value) return
  saving.value = true
  submittingFinal.value = !!submit
  try {
    const payload = Object.entries(responses).map(([criteria_row, response_text]) => ({
      criteria_row, response_text,
    }))
    const res = await api.saveFinalistSubmission({
      token: props.token,
      responses: JSON.stringify(payload),
      submit: submit ? 1 : 0,
    })
    finalist.value.status = res.status
    if (!silent) {
      toast(submit ? 'Response submitted. Thank you!' : 'Progress saved.', 'success')
    }
  } catch (e) {
    if (!silent) toast(e.message || 'Could not save.', 'error')
  } finally {
    saving.value = false
    submittingFinal.value = false
  }
}

function confirmSubmit() {
  reviewOpen.value = true
}
async function submitFinal() {
  await save(true)
  if (finalist.value?.status === 'Submitted') reviewOpen.value = false
}

async function onUpload(event, criteriaRow) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  if (!files.length) return
  uploading.value = true
  try {
    for (const f of files) {
      try {
        const res = await api.uploadFinalistAttachment(props.token, f, {
          criteria_row: criteriaRow.name,
        })
        if (res?.files) criteriaRow.response_files = res.files
      } catch (e) {
        toast(`${f.name}: ${e.message || 'upload failed'}`, 'error')
      }
    }
  } finally {
    uploading.value = false
  }
}

async function removeFile(criteriaRow, f) {
  if (!window.confirm('Remove this file?')) return
  try {
    const res = await api.deleteFinalistAttachment({
      token: props.token,
      criteria_row: criteriaRow.name,
      file_url: f.file_url,
    })
    if (res?.files) criteriaRow.response_files = res.files
  } catch (e) {
    toast(e.message || 'Could not remove file.', 'error')
  }
}

onMounted(load)
</script>
