from flask import Blueprint, jsonify

from app.auth import login_required, current_user_id
from app.database import get_db
from app.services import analytics_summary

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.get("/summary")
@login_required
def summary():
    return jsonify(analytics_summary(get_db(), current_user_id()))
