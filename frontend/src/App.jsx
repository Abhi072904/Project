import { useState, useEffect, useCallback } from 'react'
import { api } from './api.js'
import Dashboard from './components/Dashboard.jsx'
import AuthScreen from './components/AuthScreen.jsx'

export default function App() {
  const [authChecked, setAuthChecked] = useState(false)
  const [user, setUser] = useState(null)

  const [summary, setSummary] = useState(null)
  const [subscriptions, setSubscriptions] = useState([])
  const [insights, setInsights] = useState([])
  const [loading, setLoading] = useState(true)
  const [generatingInsights, setGeneratingInsights] = useState(false)
  const [loadError, setLoadError] = useState(null)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [summaryRes, subsRes, insightsRes] = await Promise.all([
        api.getAnalyticsSummary(),
        api.getSubscriptions(),
        api.getInsights(),
      ])
      setSummary(summaryRes)
      setSubscriptions(subsRes)
      setInsights(insightsRes)
      setLoadError(null)
    } catch (err) {
      setLoadError(err.message || 'Could not reach the SubSense API.')
    } finally {
      setLoading(false)
    }
  }, [])

  // On first load, check whether there's already a valid session (e.g. the
  // user refreshed the page) before deciding whether to show the login form.
  useEffect(() => {
    api
      .me()
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true))
  }, [])

  useEffect(() => {
    if (user) loadAll()
  }, [user, loadAll])

  const handleAuth = async (mode, email, password) => {
    const u = mode === 'signup' ? await api.signup(email, password) : await api.login(email, password)
    setUser(u)
  }

  const handleLogout = async () => {
    await api.logout()
    setUser(null)
    setSummary(null)
    setSubscriptions([])
    setInsights([])
  }

  const handleUpdateSubscription = async (id, updates) => {
    const updated = await api.updateSubscription(id, updates)
    setSubscriptions((prev) => prev.map((s) => (s.id === id ? updated : s)))
    const summaryRes = await api.getAnalyticsSummary()
    setSummary(summaryRes)
  }

  const handleGenerateInsights = async () => {
    setGeneratingInsights(true)
    try {
      await api.generateInsights()
      const insightsRes = await api.getInsights()
      setInsights(insightsRes)
    } finally {
      setGeneratingInsights(false)
    }
  }

  const handleUpload = async (file) => {
    const result = await api.uploadTransactions(file)
    await loadAll()
    return result
  }

  if (!authChecked) {
    return <div className="min-h-screen" />
  }

  if (!user) {
    return <AuthScreen onAuth={handleAuth} />
  }

  if (loadError) {
    return (
      <div className="min-h-screen flex items-center justify-center px-6">
        <div className="max-w-md text-center">
          <p className="font-display text-2xl text-ink mb-2">Can't reach the ledger</p>
          <p className="font-body text-sm text-ink-soft mb-4">{loadError}</p>
          <p className="font-mono text-xs text-ink-soft">
            Make sure the backend is running: <code>cd backend && python3 -m app.main</code>
          </p>
          <button
            onClick={loadAll}
            className="font-mono text-xs uppercase tracking-wide px-4 py-2 rounded bg-stamp text-paper mt-4 hover:opacity-90"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <Dashboard
      summary={summary}
      subscriptions={subscriptions}
      insights={insights}
      loading={loading}
      generatingInsights={generatingInsights}
      user={user}
      onLogout={handleLogout}
      onUpdateSubscription={handleUpdateSubscription}
      onGenerateInsights={handleGenerateInsights}
      onUpload={handleUpload}
    />
  )
}
