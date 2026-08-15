from flask import Blueprint, jsonify

from app.database import get_db
from app.services import analytics_summary

bp = Blueprint("analytics", __name__, url_prefix="/analytics")


@bp.get("/summary")
def summary():
    return jsonify(analytics_summary(get_db()))
