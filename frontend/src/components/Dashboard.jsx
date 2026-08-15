import HeroLeak from './HeroLeak.jsx'
import SubscriptionCard from './SubscriptionCard.jsx'
import SpendChart from './SpendChart.jsx'
import InsightsFeed from './InsightsFeed.jsx'
import UploadPanel from './UploadPanel.jsx'

export default function Dashboard({
  summary,
  subscriptions,
  insights,
  loading,
  generatingInsights,
  onUpdateSubscription,
  onGenerateInsights,
  onUpload,
}) {
  const sorted = [...subscriptions].sort((a, b) => {
    // flagged first (needs a decision), then active, reviewed, cancelled last
    const order = { flagged: 0, active: 1, reviewed: 2, cancelled: 3 }
    return (order[a.status] ?? 9) - (order[b.status] ?? 9) || b.annualized_cost - a.annualized_cost
  })

  return (
    <div className="max-w-5xl mx-auto px-6 py-10 md:py-14">
      <header className="mb-10 flex items-start justify-between gap-6 flex-wrap">
        <HeroLeak summary={summary} flaggedCount={summary?.flagged_count ?? 0} loading={loading} />
        <div className="w-full md:w-72 shrink-0">
          <UploadPanel onUpload={onUpload} />
        </div>
      </header>

      <div className="grid md:grid-cols-[1fr_320px] gap-8">
        <section aria-labelledby="subscriptions-heading">
          <div className="flex items-baseline justify-between mb-2">
            <h2 id="subscriptions-heading" className="font-display text-lg text-ink">
              Subscriptions
            </h2>
            <span className="font-mono text-xs text-ink-soft">
              {summary?.subscription_count ?? 0} tracked
            </span>
          </div>
          <div className="bg-paper-raised border border-line rounded-lg px-4">
            {loading ? (
              <div className="py-8 space-y-4">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="h-12 animate-pulse bg-line/40 rounded" />
                ))}
              </div>
            ) : sorted.length === 0 ? (
              <div className="py-10 text-center">
                <p className="font-body text-sm text-ink-soft">
                  No subscriptions detected yet. Upload a statement to get started.
                </p>
              </div>
            ) : (
              sorted.map((s) => (
                <SubscriptionCard key={s.id} subscription={s} onUpdate={onUpdateSubscription} />
              ))
            )}
          </div>
        </section>

        <aside className="space-y-8">
          <section aria-labelledby="breakdown-heading">
            <h2 id="breakdown-heading" className="font-display text-lg text-ink mb-2">
              Where it goes
            </h2>
            <div className="bg-paper-raised border border-line rounded-lg p-4">
              <SpendChart spendByCategory={summary?.spend_by_category} loading={loading} />
            </div>
          </section>

          <section aria-labelledby="notes-heading">
            <div className="bg-paper-raised border border-line rounded-lg p-4">
              <InsightsFeed
                insights={insights}
                loading={loading}
                generating={generatingInsights}
                onGenerate={onGenerateInsights}
                providerName={insights[0]?.provider}
              />
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
