from flask import Blueprint, request, jsonify

from app.database import get_db
from app.services import update_subscription

bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


@bp.get("")
def list_subscriptions():
    status = request.args.get("status")
    db = get_db()
    if status:
        rows = db.execute(
            "SELECT * FROM subscriptions WHERE status = ? ORDER BY annualized_cost DESC", (status,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM subscriptions ORDER BY annualized_cost DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@bp.patch("/<int:subscription_id>")
def patch_subscription(subscription_id: int):
    body = request.get_json(force=True, silent=True) or {}
    allowed = {"status", "last_used_date", "display_name"}
    updates = {k: v for k, v in body.items() if k in allowed}

    db = get_db()
    existing = db.execute("SELECT id FROM subscriptions WHERE id = ?", (subscription_id,)).fetchone()
    if not existing:
        return jsonify({"detail": "Subscription not found"}), 404

    row = update_subscription(db, subscription_id, updates)
    return jsonify(dict(row))
