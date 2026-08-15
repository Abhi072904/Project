"""
Authentication: email+password signup/login backed by Flask's signed session
cookie (itsdangerous, already a Flask dependency - no new packages needed).
Passwords are hashed with werkzeug.security (also already a Flask dependency).

This is intentionally simple - session cookie auth, not JWT/OAuth - because
the whole point is per-user data isolation, not enterprise SSO. Every table
that holds user data (transactions, subscriptions, insights) has a user_id
column, and every query in services.py is scoped by it.
"""
import re
from functools import wraps

from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

from app.database import get_db

bp = Blueprint("auth", __name__, url_prefix="/auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"detail": "Authentication required."}), 401
        return view(*args, **kwargs)

    return wrapped


def current_user_id() -> int:
    """Call only from within a login_required view - user_id is guaranteed present."""
    return session["user_id"]


def _user_json(row) -> dict:
    return {"id": row["id"], "email": row["email"], "has_real_data": bool(row["has_real_data"])}


@bp.post("/signup")
def signup():
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not _EMAIL_RE.match(email):
        return jsonify({"detail": "Enter a valid email address."}), 422
    if len(password) < 8:
        return jsonify({"detail": "Password must be at least 8 characters."}), 422

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"detail": "An account with that email already exists."}), 409

    cur = db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email, generate_password_hash(password)),
    )
    db.commit()
    new_user_id = cur.lastrowid

    # Local import to avoid a circular import (main imports auth to register
    # the blueprint; auth would otherwise need main at module load time).
    from app.main import seed_demo_data_for_user
    seed_demo_data_for_user(db, new_user_id)

    session.clear()
    session["user_id"] = new_user_id
    session.permanent = True
    # A brand-new account always starts on seed data - no query needed.
    return jsonify({"id": new_user_id, "email": email, "has_real_data": False}), 201


@bp.post("/login")
def login():
    body = request.get_json(force=True, silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"detail": "Incorrect email or password."}), 401

    session.clear()
    session["user_id"] = user["id"]
    session.permanent = True
    return jsonify(_user_json(user))


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if "user_id" not in session:
        return jsonify({"detail": "Not logged in."}), 401
    db = get_db()
    user = db.execute(
        "SELECT id, email, has_real_data FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    if not user:
        session.clear()
        return jsonify({"detail": "Not logged in."}), 401
    return jsonify(_user_json(user))
