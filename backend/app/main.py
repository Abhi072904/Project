from pathlib import Path

from flask import Flask, jsonify, request

from app.config import settings
from app.database import init_db, register_app, get_db
from app.ingestion.csv_parser import parse_transactions_csv
from app.services import ingest_transactions
from app.routers import transactions, subscriptions, insights, analytics
from app import auth


def create_app(database_path: str | None = None) -> Flask:
    app = Flask(__name__)
    if database_path:
        settings.DATABASE_PATH = database_path

    app.secret_key = settings.SECRET_KEY
    # Frontend and backend live on different domains in production (e.g.
    # vercel.app + onrender.com), so the session cookie must be cross-site:
    # SameSite=None requires Secure=True, which only works over HTTPS.
    # Locally both run on http://localhost, so we relax this for dev.
    app.config.update(
        SESSION_COOKIE_SAMESITE="None" if settings.IS_PRODUCTION else "Lax",
        SESSION_COOKIE_SECURE=settings.IS_PRODUCTION,
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,  # 30 days
    )

    register_app(app)

    @app.after_request
    def add_cors_headers(response):
        # Reflect the request's own Origin rather than "*", because
        # credentialed requests (cookies) are not allowed with a wildcard
        # origin per the CORS spec. This still isolates users from each
        # other (auth + per-row user_id do that) - it just allows any site
        # to *ask*, the same as an unauthenticated public API would.
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,OPTIONS"
        return response

    app.register_blueprint(auth.bp)
    app.register_blueprint(transactions.bp)
    app.register_blueprint(subscriptions.bp)
    app.register_blueprint(insights.bp)
    app.register_blueprint(analytics.bp)

    @app.get("/")
    def root():
        return jsonify({"service": "subsense-api", "status": "ok"})

    with app.app_context():
        init_db(settings.DATABASE_PATH)

    return app


def seed_demo_data_for_user(db, user_id: int) -> None:
    """Give a newly-signed-up user the sample dataset so their dashboard
    isn't empty on first login. Each user gets their own private copy - this
    is per-user now, not a one-time global seed, since every row is scoped
    by user_id. Real usage replaces this via /transactions/upload."""
    seed_path = Path(__file__).resolve().parent.parent / "seed_data" / "sample_transactions.csv"
    if not seed_path.exists():
        return
    parsed = parse_transactions_csv(seed_path.read_bytes(), account_label="demo-checking")
    ingest_transactions(db, user_id, parsed)
    _apply_demo_usage_overrides(db, user_id)


def _apply_demo_usage_overrides(db, user_id: int) -> None:
    # Simulate two subscriptions where the user already told the app when they
    # last actually used the service (real usage data banks don't expose) -
    # this is what makes the "unused subscription" insights show up on first run.
    overrides = {
        "Planet Fitness": "2026-06-01",
        "Peloton Interaktiv": "2026-05-02",
    }
    for merchant, last_used in overrides.items():
        db.execute(
            "UPDATE subscriptions SET last_used_date = ? WHERE merchant_normalized = ? AND user_id = ?",
            (last_used, merchant, user_id),
        )
    db.commit()
    from app.services import _apply_unused_flag
    rows = db.execute(
        "SELECT id FROM subscriptions WHERE merchant_normalized IN (?, ?) AND user_id = ?",
        (*overrides.keys(), user_id),
    ).fetchall()
    for r in rows:
        _apply_unused_flag(db, user_id, r["id"])


if __name__ == "__main__":
    import os
    flask_app = create_app()
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    flask_app.run(host="0.0.0.0", port=port, debug=debug)
