"""
Orchestration: ties the ingestion, detection, and insight layers together.
Talks to SQLite directly with parameterized SQL - no ORM. Routers stay thin
and call into here; every function takes a sqlite3.Connection so this is
fully unit-testable against an in-memory database with zero Flask/HTTP
involved (see backend/tests/test_services.py).
"""
import sqlite3
from datetime import date, datetime
from collections import defaultdict

from app.config import settings, get_insight_provider
from app.detection.recurring_detector import TxnLike, detect_all
from app.enums import SubscriptionStatus
from app.ingestion.csv_parser import ParsedTransaction
from app.insights.provider import SpendingContext, SubscriptionSummary

MONTHLY_EQUIV = {"weekly": 4.33, "monthly": 1, "quarterly": 1 / 3, "annual": 1 / 12, "irregular": 1}


def ingest_transactions(db: sqlite3.Connection, parsed: list[ParsedTransaction]) -> dict:
    db.executemany(
        """INSERT INTO transactions (txn_date, merchant_raw, merchant_normalized, amount, category, account)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [
            (p.txn_date.isoformat(), p.merchant_raw, p.merchant_normalized, p.amount, p.category, p.account)
            for p in parsed
        ],
    )
    db.commit()

    created, updated = _redetect_subscriptions(db)
    return {
        "transactions_ingested": len(parsed),
        "subscriptions_detected": created,
        "subscriptions_updated": updated,
    }


def _redetect_subscriptions(db: sqlite3.Connection) -> tuple[int, int]:
    """Re-run the recurring-charge detector over all transactions and
    create/update subscription rows. Idempotent: matches on
    (merchant_normalized, amount-cluster) so re-running after new uploads
    extends existing subscriptions instead of duplicating them."""
    rows = db.execute("SELECT id, txn_date, merchant_normalized, amount, category FROM transactions").fetchall()

    by_merchant: dict[str, list[TxnLike]] = defaultdict(list)
    txn_ids_by_merchant: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for r in rows:
        by_merchant[r["merchant_normalized"]].append(
            TxnLike(txn_date=date.fromisoformat(r["txn_date"]), amount=r["amount"])
        )
        txn_ids_by_merchant[r["merchant_normalized"]].append(r)

    detected = detect_all(by_merchant)

    created, updated = 0, 0
    for d in detected:
        existing = db.execute(
            """SELECT * FROM subscriptions
               WHERE merchant_normalized = ? AND amount BETWEEN ? AND ?""",
            (d.merchant_normalized, d.amount * 0.94, d.amount * 1.06),
        ).fetchone()

        if existing:
            sub_id = existing["id"]
            db.execute(
                """UPDATE subscriptions
                   SET last_seen = ?, amount = ?, cadence = ?, confidence = ?,
                       annualized_cost = ?, updated_at = ?
                   WHERE id = ?""",
                (d.last_seen.isoformat(), d.amount, d.cadence, d.confidence,
                 d.annualized_cost, datetime.utcnow().isoformat(), sub_id),
            )
            if existing["status"] == SubscriptionStatus.ACTIVE.value:
                _apply_unused_flag(db, sub_id)
            updated += 1
        else:
            category = next((r["category"] for r in txn_ids_by_merchant[d.merchant_normalized]), "Other")
            cur = db.execute(
                """INSERT INTO subscriptions
                   (merchant_normalized, display_name, amount, cadence, category,
                    first_seen, last_seen, status, confidence, annualized_cost)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (d.merchant_normalized, d.merchant_normalized, d.amount, d.cadence, category,
                 d.first_seen.isoformat(), d.last_seen.isoformat(),
                 SubscriptionStatus.ACTIVE.value, d.confidence, d.annualized_cost),
            )
            sub_id = cur.lastrowid
            _apply_unused_flag(db, sub_id)
            created += 1

        for r in txn_ids_by_merchant[d.merchant_normalized]:
            if d.amount * 0.94 <= r["amount"] <= d.amount * 1.06:
                db.execute(
                    "UPDATE transactions SET is_recurring = 1, subscription_id = ? WHERE id = ?",
                    (sub_id, r["id"]),
                )

    db.commit()
    return created, updated


def _apply_unused_flag(db: sqlite3.Connection, subscription_id: int) -> None:
    """Flag a subscription if it's gone quiet, based on last_used_date (user-
    reported) falling back to last_seen (last charge date) when unset."""
    row = db.execute(
        "SELECT last_used_date, last_seen FROM subscriptions WHERE id = ?", (subscription_id,)
    ).fetchone()
    reference = date.fromisoformat(row["last_used_date"] or row["last_seen"])
    days_quiet = (date.today() - reference).days
    if days_quiet >= settings.UNUSED_SUBSCRIPTION_DAYS:
        db.execute(
            "UPDATE subscriptions SET status = ? WHERE id = ?",
            (SubscriptionStatus.FLAGGED.value, subscription_id),
        )
        db.commit()


def update_subscription(db: sqlite3.Connection, subscription_id: int, updates: dict) -> sqlite3.Row | None:
    fields, values = [], []
    for col in ("status", "last_used_date", "display_name"):
        if updates.get(col) is not None:
            fields.append(f"{col} = ?")
            values.append(updates[col])
    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(subscription_id)
        db.execute(f"UPDATE subscriptions SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()
    return db.execute("SELECT * FROM subscriptions WHERE id = ?", (subscription_id,)).fetchone()


def build_spending_context(db: sqlite3.Connection) -> SpendingContext:
    subs = db.execute(
        "SELECT * FROM subscriptions WHERE status != ?", (SubscriptionStatus.CANCELLED.value,)
    ).fetchall()

    summaries, total_monthly = [], 0.0
    by_category: dict[str, float] = defaultdict(float)
    for s in subs:
        m = s["amount"] * MONTHLY_EQUIV.get(s["cadence"], 1)
        total_monthly += m
        by_category[s["category"]] += round(m, 2)
        reference = date.fromisoformat(s["last_used_date"] or s["last_seen"])
        days_since = (date.today() - reference).days
        summaries.append(
            SubscriptionSummary(
                display_name=s["display_name"],
                amount=s["amount"],
                cadence=s["cadence"],
                annualized_cost=s["annualized_cost"],
                category=s["category"],
                days_since_last_use=days_since,
            )
        )

    return SpendingContext(
        subscriptions=summaries,
        total_monthly_recurring=round(total_monthly, 2),
        total_monthly_recurring_prior_period=None,  # requires >1 statement period of history
        spend_by_category={k: round(v, 2) for k, v in by_category.items()},
    )


def generate_and_store_insights(db: sqlite3.Connection) -> list[sqlite3.Row]:
    context = build_spending_context(db)
    provider = get_insight_provider()
    batch = provider.generate_insights(context)

    name_to_id = {
        r["display_name"]: r["id"]
        for r in db.execute("SELECT id, display_name FROM subscriptions").fetchall()
    }

    ids = []
    for gi in batch.insights:
        cur = db.execute(
            """INSERT INTO insights (subscription_id, insight_type, headline, body,
                                      potential_monthly_savings, provider)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                name_to_id.get(gi.subscription_name) if gi.subscription_name else None,
                gi.insight_type, gi.headline, gi.body,
                gi.potential_monthly_savings, batch.provider_name,
            ),
        )
        ids.append(cur.lastrowid)
    db.commit()

    placeholders = ",".join("?" * len(ids)) if ids else "NULL"
    return db.execute(
        f"SELECT * FROM insights WHERE id IN ({placeholders}) ORDER BY id", ids
    ).fetchall() if ids else []


def analytics_summary(db: sqlite3.Connection) -> dict:
    context = build_spending_context(db)
    flagged = db.execute(
        "SELECT amount, cadence FROM subscriptions WHERE status = ?",
        (SubscriptionStatus.FLAGGED.value,),
    ).fetchall()
    potential_leak = sum(r["amount"] * MONTHLY_EQUIV.get(r["cadence"], 1) for r in flagged)

    active_or_flagged = db.execute(
        "SELECT annualized_cost FROM subscriptions WHERE status != ?",
        (SubscriptionStatus.CANCELLED.value,),
    ).fetchall()
    total_annualized = sum(r["annualized_cost"] for r in active_or_flagged)

    return {
        "total_monthly_recurring": context.total_monthly_recurring,
        "total_annualized_recurring": round(total_annualized, 2),
        "potential_monthly_leak": round(potential_leak, 2),
        "spend_by_category": context.spend_by_category,
        "subscription_count": len(active_or_flagged),
        "flagged_count": len(flagged),
    }
