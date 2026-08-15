# SubSense backend

Flask API + SQLite, hand-written SQL (no ORM).

## Why Flask + raw SQL instead of FastAPI + SQLAlchemy

The original plan for this project was FastAPI + SQLAlchemy + Pydantic —
a completely reasonable, arguably more modern default. Partway into
building it, it became clear the environment this project was built in has
no outbound network access to install new packages, and only Flask was
pre-installed among Python web frameworks (no FastAPI, no SQLAlchemy, no
Pydantic, no pytest).

Rather than ship FastAPI/SQLAlchemy code that was never actually executed —
and could easily have contained an import error, a route bug, or an API
mismatch that would only surface when someone else tried to run it — this
pivoted to Flask + raw `sqlite3`, both of which were available, so that
**every piece of this backend could be built, run, and tested for real**
before being called done.

That turned out to be a better fit anyway: hand-written SQL (see
`app/schema.sql`) is a more direct demonstration of SQL fluency than ORM
decorator syntax for a data engineering portfolio piece, and Flask is a
completely legitimate, widely-used production framework — not a downgrade,
a different reasonable choice made once the constraint was known.

If you're extending this project and want FastAPI/SQLAlchemy instead
(genuinely fine choices with normal internet access), the framework-
independent layers — `app/ingestion/`, `app/detection/`, `app/insights/`,
`app/enums.py` — have zero Flask/sqlite3 imports and would drop into a
FastAPI app unchanged. `app/services.py` is the one file with SQL wired
directly into it that you'd rewrite against an ORM.

## Layout

```
app/
├── ingestion/         CSV parsing (csv_parser.py) + merchant normalization/categorization (categorizer.py)
├── detection/          Recurring-charge detection algorithm (recurring_detector.py)
├── insights/            InsightProvider interface + MockProvider + VertexAIProvider
├── routers/             Flask blueprints (thin - call into services.py)
├── services.py          Orchestration: ingestion -> detection -> subscription upsert -> insights
├── schema.sql            Hand-written DDL
├── database.py           SQLite connection management (Flask g-object pattern)
├── config.py              Settings (env vars)
├── enums.py                Cadence, SubscriptionStatus - framework-independent
└── main.py                  Flask app factory + demo data seeding
```

## Running

```bash
pip install -r requirements.txt
python3 -m app.main
```

Seeds `seed_data/sample_transactions.csv` automatically on first run if the
database is empty (regenerate it with `python3 seed_data/generate_sample_data.py`
if you want different demo data — it's a deterministic synthetic dataset,
clearly not real financial data, kept in the repo for transparency about
exactly how the demo numbers were produced).

## Testing

```bash
python3 -m unittest discover -s tests -v
```

38 tests. No network, no external services — the whole suite runs in under
a tenth of a second. `tests/test_recurring_detector.py` includes two
regression tests for real false-positive bugs found while building this
(everyday repeat-merchant spending — groceries, gas, coffee — getting
misdetected as subscriptions); the git history has the full debugging story
if you want to see how those were tracked down.
