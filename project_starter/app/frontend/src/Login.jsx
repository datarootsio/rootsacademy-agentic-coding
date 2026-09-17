import { useEffect, useRef, useState } from 'react'
import { apiGet, apiPost } from './api.js'

export function Brand() {
  return <div className="brand"><span className="mark" aria-hidden="true">SS</span>
    <div><strong>Saving Streak</strong></div></div>
}

export default function Login({ onSignedIn }) {
  const [customers, setCustomers] = useState(null)
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [directoryError, setDirectoryError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const sending = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    setDirectoryError('')
    apiGet('/demo/customers', controller.signal).then(setCustomers).catch(e => {
      if (e.name !== 'AbortError') setDirectoryError(e.message)
    })
    return () => controller.abort()
  }, [attempt])

  async function signIn(address) {
    if (sending.current) return
    sending.current = true
    setBusy(true)
    setError('')
    try { onSignedIn(await apiPost('/demo/session', { email: address })) }
    catch (e) { setError(e.message) }
    finally { sending.current = false; setBusy(false) }
  }

  return <main className="login-page">
    <div className="login-story">
      <Brand />
      <div className="login-intro">
        <h1>Make room for{' '}<br />good things.</h1>
      </div>
      <div className="saving-illustration" aria-hidden="true">
        <div className="illustration-card"><strong>Save. Earn. Enjoy.</strong>
          <div className="saving-bars"><i /><i /><i /><i /><i /></div>
        </div>
      </div>
      <p className="login-footnote">Demo · No real money</p>
    </div>
    <section className="login-form-panel" aria-labelledby="welcome-title">
      <h2 id="welcome-title">Sign in</h2>
      <p className="muted">Demo access. No password needed.</p>
      {error && <p className="refusal" role="alert">{error}</p>}
      <form onSubmit={e => { e.preventDefault(); signIn(email) }}>
        <label className="field"><span className="field-label">Email address</span>
          <input type="email" autoComplete="email" required placeholder="anke@example.com"
            value={email} onChange={e => setEmail(e.target.value)} disabled={busy} /></label>
        <button className="login-submit" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}<span aria-hidden="true">→</span></button>
      </form>
      <div className="login-divider"><span>Demo profiles</span></div>
      {directoryError ? <div className="refusal" role="alert">Could not load demo profiles.
        <button className="link" onClick={() => setAttempt(attempt + 1)}>Retry</button></div>
        : customers === null ? <p role="status" className="muted">Loading demo profiles…</p>
          : <div className="demo-profiles">{customers.map((customer, index) => (
            <button className="demo-profile" key={customer.id} disabled={busy} onClick={() => signIn(customer.email)}
              aria-label={`Continue as ${customer.name}`}>
              <span className={`avatar tone-${index}`} aria-hidden="true">{customer.initials}</span>
              <span><strong>{customer.name}</strong><small>{customer.email}</small></span>
              <span className="profile-arrow" aria-hidden="true">↗</span>
            </button>
          ))}</div>}
    </section>
  </main>
}
