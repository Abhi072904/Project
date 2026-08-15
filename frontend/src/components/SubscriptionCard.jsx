const CADENCE_LABEL = { weekly: 'wk', monthly: 'mo', quarterly: 'qtr', annual: 'yr', irregular: '—' }

function daysSince(dateStr) {
  if (!dateStr) return null
  const diff = Date.now() - new Date(dateStr).getTime()
  return Math.floor(diff / (1000 * 60 * 60 * 24))
}

export default function SubscriptionCard({ subscription, onUpdate }) {
  const s = subscription
  const idle = daysSince(s.last_used_date || s.last_seen)
  const isFlagged = s.status === 'flagged'
  const isReviewed = s.status === 'reviewed'
  const isCancelled = s.status === 'cancelled'

  return (
    <div
      className={`ledger-row py-4 px-1 flex items-center gap-4 ${isCancelled ? 'opacity-50' : ''}`}
    >
      <div
        className={`w-1 self-stretch rounded-full ${
          isFlagged ? 'bg-leak' : isCancelled ? 'bg-saved' : 'bg-line'
        }`}
        aria-hidden="true"
      />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className={`font-display text-lg ${isCancelled ? 'line-through text-ink-soft' : 'text-ink'}`}>
            {s.display_name}
          </h3>
          {isReviewed && (
            <span className="audit-stamp text-stamp" title="Reviewed and kept">
              Audited
            </span>
          )}
          <span className="font-mono text-xs text-ink-soft bg-paper-raised border border-line rounded px-1.5 py-0.5">
            {s.category}
          </span>
        </div>
        <p className="font-mono text-sm text-ink-soft mt-1">
          ${s.amount.toFixed(2)}/{CADENCE_LABEL[s.cadence] ?? s.cadence}
          <span className="mx-2 text-line">·</span>
          ${s.annualized_cost.toFixed(2)}/yr
          {idle !== null && !isCancelled && (
            <>
              <span className="mx-2 text-line">·</span>
              <span className={isFlagged ? 'text-leak font-semibold' : ''}>
                {idle === 0 ? 'used today' : `${idle}d since last use`}
              </span>
            </>
          )}
        </p>
      </div>

      {!isCancelled && (
        <div className="flex gap-2 shrink-0">
          {!isReviewed && (
            <button
              onClick={() => onUpdate(s.id, { status: 'reviewed' })}
              className="font-mono text-xs uppercase tracking-wide px-3 py-1.5 rounded border border-line text-ink-soft hover:border-stamp hover:text-stamp transition-colors"
            >
              Keep
            </button>
          )}
          <button
            onClick={() => onUpdate(s.id, { status: 'cancelled' })}
            className="font-mono text-xs uppercase tracking-wide px-3 py-1.5 rounded border border-leak/40 text-leak hover:bg-leak hover:text-paper transition-colors"
          >
            Cancel
          </button>
        </div>
      )}
      {isCancelled && (
        <p className="font-mono text-xs text-saved shrink-0">
          saving ${s.amount.toFixed(2)}/{CADENCE_LABEL[s.cadence] ?? s.cadence}
        </p>
      )}
    </div>
  )
}
