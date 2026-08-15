from flask import Blueprint, request, jsonify

from app.auth import login_required, current_user_id
from app.database import get_db
from app.services import generate_and_store_insights

bp = Blueprint("insights", __name__, url_prefix="/insights")


@bp.post("/generate")
@login_required
def generate_insights():
    rows = generate_and_store_insights(get_db(), current_user_id())
    return jsonify([dict(r) for r in rows])


@bp.get("")
@login_required
def list_insights():
    limit = request.args.get("limit", default=20, type=int)
    rows = get_db().execute(
        "SELECT * FROM insights WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (current_user_id(), limit),
    ).fetchall()
    return jsonify([dict(r) for r in rows])
