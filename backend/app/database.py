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
    """Create tables if they don't exist, then apply any additive migrations.
    Safe to call on every startup - existing installs get upgraded in place
    instead of requiring the database to be deleted and recreated."""
    conn = sqlite3.connect(db_path or settings.DATABASE_PATH)
    try:
        conn.executescript(_SCHEMA_PATH.read_text())
        conn.commit()
        _run_migrations(conn)
    finally:
        conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Columns added after the initial schema go here. SQLite has no
    ALTER TABLE ... ADD COLUMN IF NOT EXISTS, so we attempt the change and
    swallow the "duplicate column" error on installs that already have it
    (including brand-new databases, where schema.sql just created it)."""
    try:
        conn.execute("ALTER TABLE users ADD COLUMN has_real_data INTEGER NOT NULL DEFAULT 0")
        # One-time backfill: an account created before this column existed
        # may already have uploaded a real statement. Anyone with a
        # transaction outside the fixed "demo-checking" seed label has real
        # data, even though the new column defaulted to 0 for everyone.
        conn.execute(
            """UPDATE users SET has_real_data = 1 WHERE id IN (
                   SELECT DISTINCT user_id FROM transactions
                   WHERE account IS NULL OR account != 'demo-checking'
               )"""
        )
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise


def register_app(app):
    app.teardown_appcontext(close_db)
