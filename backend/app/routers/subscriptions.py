from flask import Blueprint, request, jsonify

from app.auth import login_required, current_user_id
from app.database import get_db
from app.services import update_subscription

bp = Blueprint("subscriptions", __name__, url_prefix="/subscriptions")


@bp.get("")
@login_required
def list_subscriptions():
    status = request.args.get("status")
    db = get_db()
    user_id = current_user_id()
    if status:
        rows = db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? AND status = ? ORDER BY annualized_cost DESC",
            (user_id, status),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY annualized_cost DESC", (user_id,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.patch("/<int:subscription_id>")
@login_required
def patch_subscription(subscription_id: int):
    body = request.get_json(force=True, silent=True) or {}
    allowed = {"status", "last_used_date", "display_name"}
    updates = {k: v for k, v in body.items() if k in allowed}

    db = get_db()
    user_id = current_user_id()
    existing = db.execute(
        "SELECT id FROM subscriptions WHERE id = ? AND user_id = ?", (subscription_id, user_id)
    ).fetchone()
    if not existing:
        return jsonify({"detail": "Subscription not found"}), 404

    row = update_subscription(db, user_id, subscription_id, updates)
    return jsonify(dict(row))
