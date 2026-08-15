from flask import Blueprint, request, jsonify

from app.database import get_db
from app.ingestion.csv_parser import parse_transactions_csv, CSVParseError
from app.services import ingest_transactions

bp = Blueprint("transactions", __name__, url_prefix="/transactions")


@bp.post("/upload")
def upload_transactions():
    if "file" not in request.files:
        return jsonify({"detail": "No file provided (expected multipart field 'file')."}), 422

    file = request.files["file"]
    account_label = request.form.get("account_label")
    content = file.read()

    try:
        parsed = parse_transactions_csv(content, account_label=account_label)
    except CSVParseError as e:
        return jsonify({"detail": str(e)}), 422

    if not parsed:
        return jsonify({"detail": "No valid transaction rows found in file."}), 422

    result = ingest_transactions(get_db(), parsed)
    return jsonify(result)


@bp.get("")
def list_transactions():
    limit = request.args.get("limit", default=200, type=int)
    rows = get_db().execute(
        "SELECT * FROM transactions ORDER BY txn_date DESC LIMIT ?", (limit,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])
