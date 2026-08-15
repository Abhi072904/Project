import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

// Ledger palette, not default recharts colors - kept in step with the design tokens
const PALETTE = ['#2B3A67', '#D6482F', '#2F6F4E', '#8A7B5C', '#5B6B7A', '#B23A2E', '#4A6670', '#9C8ADE']

export default function SpendChart({ spendByCategory, loading }) {
  const entries = Object.entries(spendByCategory || {}).sort((a, b) => b[1] - a[1])
  const total = entries.reduce((sum, [, v]) => sum + v, 0)

  if (loading) {
    return <div className="h-64 animate-pulse bg-line/40 rounded" />
  }

  if (entries.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-center text-ink-soft font-body text-sm px-6">
        No recurring spend yet. Upload a statement to see the breakdown.
      </div>
    )
  }

  const data = entries.map(([name, value]) => ({ name, value }))

  return (
    <div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            innerRadius={55}
            outerRadius={90}
            paddingAngle={2}
            stroke="none"
          >
            {data.map((entry, i) => (
              <Cell key={entry.name} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [`$${value.toFixed(2)}/mo`, null]}
            contentStyle={{
              fontFamily: 'IBM Plex Mono, monospace',
              fontSize: 12,
              border: '1px solid #D8DACE',
              borderRadius: 4,
            }}
          />
        </PieChart>
      </ResponsiveContainer>
      <ul className="mt-2 space-y-1.5">
        {data.map((entry, i) => (
          <li key={entry.name} className="flex items-center justify-between text-sm font-body">
            <span className="flex items-center gap-2 text-ink-soft">
              <span
                className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ backgroundColor: PALETTE[i % PALETTE.length] }}
                aria-hidden="true"
              />
              {entry.name}
            </span>
            <span className="font-mono text-ink tabular-nums">
              ${entry.value.toFixed(2)}
              <span className="text-ink-soft ml-1.5">
                {total > 0 ? `${Math.round((entry.value / total) * 100)}%` : ''}
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
