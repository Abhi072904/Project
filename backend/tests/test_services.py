import sqlite3
import unittest
from pathlib import Path
from datetime import date

from app import services
from app.ingestion.csv_parser import parse_transactions_csv

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "app" / "schema.sql"


def make_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text())
    return conn


SAMPLE_CSV = b"""date,description,amount
2026-01-05,NETFLIX.COM 866-579-7172,15.99
2026-02-04,NETFLIX.COM 866-579-7172,15.99
2026-03-06,NETFLIX.COM 866-579-7172,15.99
2026-04-05,NETFLIX.COM 866-579-7172,15.99
2026-01-10,SQ *PLANET FITNESS #4021,24.99
2026-02-09,SQ *PLANET FITNESS #4021,24.99
2026-03-11,SQ *PLANET FITNESS #4021,24.99
2026-01-20,WHOLE FOODS MKT,88.40
2026-02-14,WHOLE FOODS MKT,52.10
"""


class TestIngestAndDetect(unittest.TestCase):
    def setUp(self):
        self.db = make_db()

    def tearDown(self):
        self.db.close()

    def test_ingest_creates_transactions_and_subscriptions(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        result = services.ingest_transactions(self.db, parsed)

        self.assertEqual(result["transactions_ingested"], 9)
        self.assertEqual(result["subscriptions_detected"], 2)  # Netflix + Planet Fitness

        txn_count = self.db.execute("SELECT COUNT(*) AS n FROM transactions").fetchone()["n"]
        self.assertEqual(txn_count, 9)

        subs = self.db.execute("SELECT * FROM subscriptions ORDER BY display_name").fetchall()
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["display_name"], "Netflix")

    def test_grocery_purchases_are_not_flagged_as_subscriptions(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, parsed)
        merchants = [r["merchant_normalized"] for r in self.db.execute("SELECT merchant_normalized FROM subscriptions").fetchall()]
        self.assertNotIn("Whole Foods Mkt", merchants)

    def test_reingesting_more_data_updates_not_duplicates(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, parsed)

        more = parse_transactions_csv(
            b"date,description,amount\n2026-05-05,NETFLIX.COM 866-579-7172,15.99\n"
        )
        services.ingest_transactions(self.db, more)

        subs = self.db.execute("SELECT * FROM subscriptions WHERE display_name = 'Netflix'").fetchall()
        self.assertEqual(len(subs), 1)  # still one row, not a duplicate
        self.assertEqual(subs[0]["last_seen"], "2026-05-05")

    def test_unused_flag_applied_when_last_used_date_is_old(self):
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, parsed)

        sub = self.db.execute("SELECT id FROM subscriptions WHERE display_name = 'Sq Planet Fitness'").fetchone()
        self.db.execute("UPDATE subscriptions SET last_used_date = '2026-01-01' WHERE id = ?", (sub["id"],))
        self.db.commit()
        services._apply_unused_flag(self.db, sub["id"])

        status = self.db.execute("SELECT status FROM subscriptions WHERE id = ?", (sub["id"],)).fetchone()["status"]
        self.assertEqual(status, "flagged")


class TestUpdateSubscription(unittest.TestCase):
    def setUp(self):
        self.db = make_db()
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(self.db, parsed)
        self.sub_id = self.db.execute("SELECT id FROM subscriptions LIMIT 1").fetchone()["id"]

    def tearDown(self):
        self.db.close()

    def test_mark_reviewed_stamp(self):
        row = services.update_subscription(self.db, self.sub_id, {"status": "reviewed"})
        self.assertEqual(row["status"], "reviewed")

    def test_mark_cancelled_removes_from_active_totals(self):
        before = services.analytics_summary(self.db)
        services.update_subscription(self.db, self.sub_id, {"status": "cancelled"})
        after = services.analytics_summary(self.db)
        self.assertLess(after["total_monthly_recurring"], before["total_monthly_recurring"])


class TestAnalyticsSummary(unittest.TestCase):
    def test_potential_leak_reflects_flagged_subscriptions_only(self):
        db = make_db()
        parsed = parse_transactions_csv(SAMPLE_CSV)
        services.ingest_transactions(db, parsed)

        summary_before = services.analytics_summary(db)
        self.assertEqual(summary_before["flagged_count"], 0)
        self.assertEqual(summary_before["potential_monthly_leak"], 0)

        sub = db.execute("SELECT id FROM subscriptions WHERE display_name = 'Netflix'").fetchone()
        db.execute("UPDATE subscriptions SET last_used_date = '2025-01-01' WHERE id = ?", (sub["id"],))
        db.commit()
        services._apply_unused_flag(db, sub["id"])

        summary_after = services.analytics_summary(db)
        self.assertEqual(summary_after["flagged_count"], 1)
        self.assertAlmostEqual(summary_after["potential_monthly_leak"], 15.99)
        db.close()


if __name__ == "__main__":
    unittest.main()
