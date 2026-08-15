-- SubSense schema.
-- SQLite for local/demo use; every statement here is portable ANSI SQL that
-- runs unmodified on Postgres too (see docs/ARCHITECTURE.md for the swap notes).

CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    email               TEXT    NOT NULL UNIQUE,
    password_hash       TEXT    NOT NULL,
    has_real_data       INTEGER NOT NULL DEFAULT 0,     -- 0 until they upload their own statement
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    txn_date            TEXT    NOT NULL,              -- ISO date
    merchant_raw        TEXT    NOT NULL,
    merchant_normalized TEXT    NOT NULL,
    amount              REAL    NOT NULL,
    category            TEXT    NOT NULL DEFAULT 'Other',
    account             TEXT,
    is_recurring        INTEGER NOT NULL DEFAULT 0,     -- 0/1 boolean
    subscription_id     INTEGER REFERENCES subscriptions(id),
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant_normalized);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(txn_date);

CREATE TABLE IF NOT EXISTS subscriptions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL REFERENCES users(id),
    merchant_normalized TEXT    NOT NULL,
    display_name        TEXT    NOT NULL,
    amount              REAL    NOT NULL,
    cadence             TEXT    NOT NULL DEFAULT 'monthly',
    category            TEXT    NOT NULL DEFAULT 'Other',
    first_seen          TEXT    NOT NULL,
    last_seen           TEXT    NOT NULL,
    last_used_date      TEXT,                            -- nullable: user-reported
    status               TEXT    NOT NULL DEFAULT 'active',
    confidence          REAL    NOT NULL DEFAULT 0.0,
    annualized_cost     REAL    NOT NULL DEFAULT 0.0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_merchant ON subscriptions(merchant_normalized);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);

CREATE TABLE IF NOT EXISTS insights (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id                     INTEGER NOT NULL REFERENCES users(id),
    created_at                  TEXT    NOT NULL DEFAULT (datetime('now')),
    subscription_id             INTEGER REFERENCES subscriptions(id),
    insight_type                TEXT    NOT NULL,
    headline                    TEXT    NOT NULL,
    body                        TEXT    NOT NULL,
    potential_monthly_savings   REAL    NOT NULL DEFAULT 0.0,
    provider                    TEXT    NOT NULL DEFAULT 'mock'
);

CREATE INDEX IF NOT EXISTS idx_insights_user ON insights(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_created ON insights(created_at);
