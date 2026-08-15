# SubSense frontend

React + Vite + Tailwind + Recharts.

**Verification note:** this was written in a sandboxed build environment
with no npm registry access, so Vite/Tailwind/Recharts couldn't actually be
installed and the dev server was never booted. What *was* verified:

- Every JSX file is syntax-checked clean (`npx tsc --jsx react-jsx --noEmit ...`).
- Every import statement was cross-checked against the target file's actual
  exports — no typos, no missing exports.
- Every custom Tailwind color class used in a component was cross-checked
  against `tailwind.config.js` — no undefined-class typos.
- The exact request/response contract `src/api.js` depends on (every
  endpoint, including the multipart file upload) was tested with real
  `fetch()` calls against the live backend before these components were
  written, so the data layer this UI is built on is solid even though the
  rendering layer isn't boot-tested.

Run `npm install && npm run dev` to see it live — that's genuinely the next
step, not a formality.

## Design system

Grounded in the subject (a financial ledger/audit, not a generic SaaS
dashboard): a cool paper background instead of the common warm-cream
default, an ink-navy/burnt-red/sage palette, Fraunces serif for numbers and
headlines paired with Inter for body text and IBM Plex Mono for anything
financial (amounts, dates, categories — the "ledger" register). The
signature element is the rotated "AUDITED" ink-stamp mark that appears when
you mark a subscription reviewed.

## Structure

```
src/
├── api.js                Backend client - plain JS, verified against live API
├── App.jsx                 Data fetching + top-level state
├── index.css                 Tailwind + design tokens + the stamp/underline primitives
└── components/
    ├── Dashboard.jsx           Layout
    ├── HeroLeak.jsx              The big "$X/mo leaking" stat
    ├── SubscriptionCard.jsx        Audit list item + the stamp interaction
    ├── SpendChart.jsx                Category breakdown (recharts)
    ├── InsightsFeed.jsx                AI notes feed
    └── UploadPanel.jsx                   CSV drag-and-drop
```
