import sqlite3
from pathlib import Path

from flask import g

from app.config import settings

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db() -> sqlite3.Connection:
    """Request-scoped connection, following Flask's standard g-object pattern."""
    if "db" not in g:
        g.db = sqlite3.connect(settings.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(db_path: str | None = None):
    """Create tables if they don't exist. Safe to call on every startup."""
    conn = sqlite3.connect(db_path or settings.DATABASE_PATH)
    try:
        conn.executescript(_SCHEMA_PATH.read_text())
        conn.commit()
    finally:
        conn.close()


def register_app(app):
    app.teardown_appcontext(close_db)
