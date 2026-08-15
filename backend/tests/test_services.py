import sqlite3
import unittest
from pathlib import Path
from datetime import date, timedelta

from app import services
from app.ingestion.csv_parser import parse_transactions_csv

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "app" / "schema.sql"


def make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


def make_user(conn: sqlite3.Connection) -> int:
    """Every table is user-scoped now; tests need a real user row to attach
    fixtures to, same as the app requires a signed-up account."""
    cur = conn.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("test@example.com", "not-a-real-hash"),
    )
    conn.commit()
    return cur.lastrowid


def _d(days_ago: int) -> str:
    """ISO date `days_ago` days before today - keeps fixtures valid no matter
    when the test suite runs, instead of drifting stale against a hardcoded
    date (this bit us: the original fixture used fixed Jan-Apr 2026 dates,
    which quietly became 45+ days old and started tripping the unused-flag
    logic in tests that never meant to exercise it)."""
    return (date.today() - timedelta(days=days_ago)).isoformat()


SAMPLE_CSV = f"""date,description,amount
{_d(127)},NETFLIX.COM 866-579-7172,15.99
{_d(97)},NETFLIX.COM 866-579-7172,15.99
{_d(67)},NETFLIX.COM 866-579-7172,15.99
{_d(37)},NETFLIX.COM 866-579-7172,15.99
{_d(92)},SQ *PLANET FITNESS #4021,24.99
{_d(62)},SQ *PLANET FITNESS #4021,24.99
{_d(32)},SQ *PLANET FITNESS #4021,24.99
{_d(85)},WHOLE FOODS MKT,88.40
{_d(50)},WHOLE FOODS MKT,52.10
""".encode()


class TestIngestAndDetect(unittest.TestCase):
    def setUp(self):
        self.db = make_db()
        self.user_id = make_user(self.db)

    def tearDown(self):
        self.db.close()

    def test_ingest_creates_transactions_and_subscriptions(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        result = services.ingest_transactions(self.db, self.user_id, parsed)

        self.assertEqual(result["transactions_ingested"], 9)
        self.assertEqual(result["subscriptions_detected"], 2)  # Netflix + Planet Fitness

        txn_count = self.db.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
        self.assertEqual(txn_count, 9)

        subs = self.db.execute("SELECT * FROM subscriptions ORDER BY display_name").fetchall()
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["display_name"], "Netflix")

    def test_grocery_purchases_are_not_flagged_as_subscriptions(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, self.user_id, parsed)
        merchants = [r["merchant_normalized"] for r in self.db.execute("SELECT merchant_normalized FROM subscriptions").fetchall()]
        self.assertNotIn("Whole Foods Mkt", merchants)

    def test_reuploading_identical_data_is_deduplicated(self):
        # Realistic scenario: user re-exports a statement with an overlapping
        # date range and uploads it again. Exact-duplicate rows should be
        # skipped, not inserted a second time.
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, self.user_id, parsed)

        result = services.ingest_transactions(self.db, self.user_id, parse_transactions_csv(SAMPLE_CSV))
        self.assertEqual(result["transactions_ingested"], 0)
        self.assertEqual(result["duplicates_skipped"], 9)

        total = self.db.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
        self.assertEqual(total, 9)  # not 18

    def test_reingesting_more_data_updates_not_duplicates(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, self.user_id, parsed)

        newest_date = _d(7)  # ~30 days after the existing series' last charge (_d(37)) - realistic monthly spacing
        more = parse_transactions_csv(
            f"date,description,amount\n{newest_date},NETFLIX.COM 866-579-7172,15.99\n".encode()
        )
        services.ingest_transactions(self.db, self.user_id, more)

        subs = self.db.execute("SELECT * FROM subscriptions WHERE display_name = 'Netflix'").fetchall()
        self.assertEqual(len(subs), 1)  # still one row, not a duplicate
        self.assertEqual(subs[0]["last_seen"], newest_date)

    def test_unused_flag_applied_when_last_used_date_is_old(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, self.user_id, parsed)

        sub = self.db.execute("SELECT id FROM subscriptions WHERE display_name = 'Planet Fitness'").fetchone()
        self.db.execute("UPDATE subscriptions SET last_used_date = ? WHERE id = ?", (_d(90), sub["id"]))
        self.db.commit()
        services._apply_unused_flag(self.db, self.user_id, sub["id"])

        status = self.db.execute("SELECT status FROM subscriptions WHERE id = ?", (sub["id"],)).fetchone()["status"]
        self.assertEqual(status, "flagged")


class TestUpdateSubscription(unittest.TestCase):
    def setUp(self):
        self.db = make_db()
        self.user_id = make_user(self.db)
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, self.user_id, parsed)
        self.sub_id = self.db.execute("SELECT id FROM subscriptions LIMIT 1").fetchone()["id"]

    def tearDown(self):
        self.db.close()

    def test_mark_reviewed_stamp(self):
        row = services.update_subscription(self.db, self.user_id, self.sub_id, {"status": "reviewed"})
        self.assertEqual(row["status"], "reviewed")

    def test_mark_cancelled_removes_from_active_totals(self):
        before = services.analytics_summary(self.db, self.user_id)
        services.update_subscription(self.db, self.user_id, self.sub_id, {"status": "cancelled"})
        after = services.analytics_summary(self.db, self.user_id)
        self.assertLess(after["total_monthly_recurring"], before["total_monthly_recurring"])


class TestAnalyticsSummary(unittest.TestCase):
    def test_potential_leak_reflects_flagged_subscriptions_only(self):
        db = make_db()
        user_id = make_user(db)
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(db, user_id, parsed)

        summary_before = services.analytics_summary(db, user_id)
        self.assertEqual(summary_before["flagged_count"], 0)
        self.assertEqual(summary_before["potential_monthly_leak"], 0)

        sub = db.execute("SELECT id FROM subscriptions WHERE display_name = 'Netflix'").fetchone()
        db.execute("UPDATE subscriptions SET last_used_date = ? WHERE id = ?", (_d(90), sub["id"]))
        db.commit()
        services._apply_unused_flag(db, user_id, sub["id"])

        summary_after = services.analytics_summary(db, user_id)
        self.assertEqual(summary_after["flagged_count"], 1)
        self.assertAlmostEqual(summary_after["potential_monthly_leak"], 15.99)
        db.close()


if __name__ == "__main__":
    unittest.main()
