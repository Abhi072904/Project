from pathlib import Path

from flask import Flask, jsonify

from app.config import settings
from app.database import init_db, register_app, get_db
from app.ingestion.csv_parser import parse_transactions_csv
from app.services import ingest_transactions
from app.routers import transactions, subscriptions, insights, analytics


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)
    if database_path:
        settings.DATABASE_PATH = database_path

    register_app(app)

    @app.after_request
    def add_cors_headers(response):
        # Permissive CORS for local dev (frontend runs on a different port).
        # Tighten this to a specific origin allowlist before deploying publicly.
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,OPTIONS"
        return response

    app.register_blueprint(transactions.bp)
    app.register_blueprint(subscriptions.bp)
    app.register_blueprint(insights.bp)
    app.register_blueprint(analytics.bp)

    @app.get("/")
    def root():
        return jsonify({"service": "subsense-api", "status": "ok"})

    with app.app_context():
        init_db(settings.DATABASE_PATH)
        _seed_if_empty()

    return app


def _seed_if_empty():
    """First-run convenience: load the sample dataset so the dashboard isn't
    empty on a fresh clone. Real usage replaces this via /transactions/upload."""
    db = get_db()
    count = db.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
    if count > 0:
        return
    seed_path = Path(__file__).resolve().parent.parent / "seed_data" / "sample_transactions.csv"
    if not seed_path.exists():
        return
    parsed = parse_transactions_csv(seed_path.read_bytes(), account_label="demo-checking")
    ingest_transactions(db, parsed)

    # Simulate two subscriptions where the user already told the app when they
    # last actually used the service (real usage data banks don't expose) -
    # this is what makes the "unused subscription" insights show up on first run.
    _apply_demo_usage_overrides(db)


def _apply_demo_usage_overrides(db):
    overrides = {
        "Planet Fitness": "2026-06-01",
        "Peloton Interaktiv": "2026-05-02",
    }
    for merchant, last_used in overrides.items():
        db.execute(
            "UPDATE subscriptions SET last_used_date = ? WHERE merchant_normalized = ?",
            (last_used, merchant),
        )
    db.commit()
    from app.services import _apply_unused_flag
    rows = db.execute("SELECT id FROM subscriptions WHERE merchant_normalized IN (?, ?)",
                       tuple(overrides.keys())).fetchall()
    for r in rows:
        _apply_unused_flag(db, r["id"])


if __name__ == "__main__":
    import os
    flask_app = create_app()
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    flask_app.run(host="0.0.0.0", port=port, debug=debug)
