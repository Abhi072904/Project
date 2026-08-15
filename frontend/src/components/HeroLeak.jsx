export default function HeroLeak({ summary, flaggedCount, loading }) {
  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-16 w-80 bg-line/60 rounded" />
        <div className="h-4 w-56 bg-line/40 rounded mt-3" />
      </div>
    )
  }

  const leak = summary?.potential_monthly_leak ?? 0
  const hasLeak = leak > 0

  return (
    <div>
      <p className="font-mono text-xs uppercase tracking-[0.2em] text-ink-soft mb-2">
        This period's audit
      </p>
      <div className="flex items-baseline gap-3 flex-wrap">
        <h1 className="font-display text-6xl md:text-7xl font-semibold tabular-nums">
          ${leak.toFixed(2)}
        </h1>
        <span className="font-body text-lg text-ink-soft">/mo detected leaking</span>
      </div>
      {hasLeak && <div className="hero-underline w-64 mt-1" aria-hidden="true" />}
      <p className="font-body text-ink-soft mt-4 max-w-xl">
        {hasLeak ? (
          <>
            Across <span className="font-semibold text-ink">{flaggedCount}</span>{' '}
            {flaggedCount === 1 ? 'subscription' : 'subscriptions'} you haven't touched in 45+ days.
            Cancel below, or stamp them "audited" to keep them.
          </>
        ) : (
          "Nothing flagged this period — every recurring charge shows recent activity."
        )}
      </p>
    </div>
  )
}
