// The only way the UI reaches the domain. Every call lands on the
// application-service seam of spec D42; nothing here decides a rule.

export async function apiGet(path, signal) {
  const response = await fetch(`/api${path}`, { signal })
  if (!response.ok) {
    throw new Error(await refusal(response, 'GET', path))
  }
  return response.json()
}

export async function apiPost(path, body) {
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(await refusal(response, 'POST', path))
  }
  return response.json()
}

// The seam says why it refused; the UI only has to read it out. It decides
// nothing about the refusal — a rule lives behind the seam, not here.
//
// Reads are refused too, not only writes: a read is taken at an instant, and
// the seam will not read at one past the end of its calendar. A page that
// showed the status code for that and the domain's own sentence for an
// oversized withdrawal would be inventing a difference the seam does not make.
async function refusal(response, method, path) {
  const text = await response.text()
  try {
    const detail = JSON.parse(text).detail
    if (typeof detail === 'string' && detail) return detail
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d) => `${(d.loc ?? []).join('.')}: ${d.msg}`).join('; ')
    }
  } catch {
    // Not a JSON body; fall through to the raw text.
  }
  return `${method} ${path} failed: ${response.status} ${text}`.trim()
}

// One idempotency key per claim attempt (spec D15). `crypto.randomUUID` is
// there on a secure origin, which 127.0.0.1 is; the fallback keeps a claim
// possible if the page is ever opened somewhere it is not.
export function newIdempotencyKey() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `key-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
}
