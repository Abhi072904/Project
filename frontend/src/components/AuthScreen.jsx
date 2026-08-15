import { useState } from 'react'

export default function AuthScreen({ onAuth }) {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await onAuth(mode, email, password)
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-ink-soft text-center mb-2">
          SubSense
        </p>
        <h1 className="font-display text-2xl text-ink text-center mb-8">
          {mode === 'login' ? 'Welcome back' : 'Open your ledger'}
        </h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="font-mono text-xs uppercase tracking-wide text-ink-soft block mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full font-body text-sm border border-line rounded px-3 py-2 bg-paper-raised text-ink focus:outline-none"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label htmlFor="password" className="font-mono text-xs uppercase tracking-wide text-ink-soft block mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full font-body text-sm border border-line rounded px-3 py-2 bg-paper-raised text-ink focus:outline-none"
              placeholder={mode === 'signup' ? 'At least 8 characters' : '••••••••'}
            />
          </div>

          {error && <p className="font-body text-xs text-leak">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full font-mono text-xs uppercase tracking-wide px-4 py-2.5 rounded bg-stamp text-paper hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {submitting ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>

        <p className="font-body text-xs text-ink-soft text-center mt-6">
          {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
          <button
            type="button"
            onClick={() => {
              setMode(mode === 'login' ? 'signup' : 'login')
              setError(null)
            }}
            className="text-stamp hover:underline"
          >
            {mode === 'login' ? 'Sign up' : 'Log in'}
          </button>
        </p>

        {mode === 'signup' && (
          <p className="font-body text-xs text-ink-soft text-center mt-3">
            Your account starts with sample data so the dashboard isn't empty — upload your own
            statement any time to replace it.
          </p>
        )}
      </div>
    </div>
  )
}
