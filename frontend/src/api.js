// Thin wrapper over fetch for Frappe whitelisted methods.
function getCsrfToken() {
  // 1. Token injected into window by the Jinja boot block (matches Frappe CRM).
  const wt = typeof window !== 'undefined' ? window.csrf_token : ''
  if (wt && wt !== '{{ csrf_token }}') return wt
  // 2. Fallback to the cookie set by Frappe for authenticated sessions.
  const m = document.cookie.match(/(?:^|; )csrf_token=([^;]+)/)
  return m ? decodeURIComponent(m[1]) : ''
}

async function call(method, { params, body } = {}) {
  const url = new URL(`/api/method/${method}`, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => v != null && url.searchParams.set(k, v))
  const init = {
    method: body ? 'POST' : 'GET',
    headers: {
      'X-Frappe-CSRF-Token': getCsrfToken() || 'token',
      'Accept': 'application/json',
    },
  }
  if (body) {
    init.headers['Content-Type'] = 'application/x-www-form-urlencoded'
    init.body = new URLSearchParams(body).toString()
  }
  const r = await fetch(url, init)
  let data = null
  try { data = await r.json() } catch (_) { /* */ }
  if (!r.ok) {
    const msg = data?._server_messages
      ? safeParseServerMessages(data._server_messages)
      : data?.exception || data?.message || `Request failed (${r.status})`
    const err = new Error(msg)
    err.status = r.status
    throw err
  }
  return data?.message
}

function safeParseServerMessages(raw) {
  try {
    const arr = JSON.parse(raw)
    return arr.map((m) => {
      try { return JSON.parse(m).message } catch { return m }
    }).join(' ')
  } catch { return raw }
}

export default {
  getCampaign: (slug) => call('nominations.api.get_campaign', { params: { slug } }),
  getAward: (campaign_slug, award_slug) => call('nominations.api.get_award', { params: { campaign_slug, award_slug } }),
  getNominee: (nomination_id) => call('nominations.api.get_nominee', { params: { nomination_id } }),
  requestOtp: (body) => call('nominations.api.request_otp', { body }),
  verifyOtp: (body) => call('nominations.api.verify_otp', { body }),
  submitNomination: (body) => call('nominations.api.submit_nomination', { body }),
  submitVote: (body) => call('nominations.api.submit_vote', { body }),
  uploadFile: async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch('/api/method/nominations.api.upload_nominee_photo', {
      method: 'POST',
      headers: {
        'X-Frappe-CSRF-Token': getCsrfToken() || 'token',
        'Accept': 'application/json',
      },
      body: fd,
    })
    let d = null
    try { d = await r.json() } catch (_) { /* */ }
    if (!r.ok) {
      const msg = d?._server_messages
        ? safeParseServerMessages(d._server_messages)
        : d?.exception || d?.message || `Upload failed (${r.status})`
      throw new Error(msg)
    }
    return d?.message
  },
}
