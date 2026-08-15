# SubSense

**Find the subscriptions you forgot you're paying for — free, self-hosted, no subscription required to audit your subscriptions.**

Rocket Money and Copilot Money charge $6–12/month to tell you what you're
already paying for. SubSense does the same core job — detect recurring
charges, flag the ones you've stopped using, explain what to cut — as
something you run yourself.

## What it does

Upload a bank or card statement CSV. SubSense:

1. **Normalizes and categorizes** every transaction (`SQ *PLANET FITNESS #4021` → `Planet Fitness`, Fitness & Health).
2. **Detects recurring charges** — clusters same-merchant transactions by amount, checks whether the interval between charges is consistent enough to call it a real subscription (weekly/monthly/quarterly/annual), and scores a confidence.
3. **Flags what's gone quiet** — subscriptions with no logged usage in 45+ days surface as a "leak."
4. **Generates plain-language insights** — "Peloton hasn't been touched in 103 days, cancelling frees up $44/mo" — via a swappable AI provider (Vertex AI in production, a deterministic mock locally).
5. **Tracks it on a dashboard** — one hero number (total monthly leak), a spend-by-category breakdown, and an audit list where you stamp a subscription "kept" or cancel it.

## Why this exists

This was built to replace a specific hackathon project (an AI study-tool
web app) with something that (a) covers the same underlying skills — GenAI
model integration, AWS Glue ETL, Athena serverless SQL, engagement-driven
analytics — and (b) solves a real problem instead of a class assignment.
Full writeup: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | Flask + raw SQL (sqlite3) | See [`backend/README.md`](backend/README.md) — no ORM was available in the build environment, so this went with hand-written SQL, which is arguably a stronger signal for a data role anyway |
| Detection algorithm | Pure Python, rule-based | Explainable — a user auditing their money should see *why* something got flagged, not trust a black box |
| AI insights | Vertex AI (Gemini), swappable to a local mock provider | Same "provider interface, swap the implementation" pattern used for the Claude/OpenAI split behind the Pfizer patient-matching engine this project's author built professionally |
| Batch ETL | AWS Glue (PySpark) → S3 (Parquet) → Athena | Warehouse-scale counterpart to the API's per-upload path |
| Frontend | React + Tailwind + Recharts | See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#whats-verified-vs-what's-reviewed) for an honest note on build-verification status |

## Quickstart

### Backend

```bash
cd backend
pip install -r requirements.txt
python3 -m app.main
# API on http://127.0.0.1:8000, auto-seeds demo data on first run
```

Run the tests (38 of them, all passing, zero network required):

```bash
cd backend
python3 -m unittest discover -s tests -v
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Dashboard on http://127.0.0.1:5173, proxies API calls to :8000
```

### AWS ETL layer (optional — for warehouse-scale batch processing)

See [`etl/README.md`](etl/README.md) for deploying the Glue job and Athena
tables to a real AWS account.

## Project structure

```
subsense/
├── backend/           Flask API, SQLite, detection algorithm, tests
│   ├── app/
│   │   ├── ingestion/      CSV parsing + merchant categorization
│   │   ├── detection/      Recurring-charge detection algorithm
│   │   ├── insights/       AI provider interface (Mock + Vertex AI)
│   │   └── routers/        Flask blueprints
│   ├── tests/               38 unit + integration tests
│   └── seed_data/          Synthetic demo data + its generator script
├── etl/                Glue job, Athena DDL + analytical queries
├── frontend/           React dashboard
└── docs/
    └── ARCHITECTURE.md  System design, diagram, verification status
```

## Skills this demonstrates

Carried over from the project this replaced: GenAI model integration and
inference (Vertex AI), AWS Glue ETL, Athena serverless SQL querying, and an
analytics dashboard built on engagement-style data (here, subscription
usage recency instead of quiz difficulty).

Added on top: a provider-abstracted AI integration layer, a from-scratch
recurring-pattern detection algorithm (with real false-positive bugs found
and fixed during development — see the git history), a full REST API with
38 passing tests, warehouse-scale batch ETL as a second ingestion path into
the same data model, and a designed (not templated) frontend.

## License

MIT — see [`LICENSE`](LICENSE).
