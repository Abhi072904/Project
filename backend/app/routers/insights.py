from flask import Blueprint, request, jsonify

from app.database import get_db
from app.services import generate_and_store_insights

bp = Blueprint("insights", __name__, url_prefix="/insights")


@bp.post("/generate")
def generate_insights():
    rows = generate_and_store_insights(get_db())
    return jsonify([dict(r) for r in rows])


@bp.get("")
def list_insights():
    limit = request.args.get("limit", default=20, type=int)
    rows = get_db().execute(
        "SELECT * FROM insights ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])
