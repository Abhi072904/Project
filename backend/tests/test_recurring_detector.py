import unittest
from datetime import date, timedelta

from app.detection.recurring_detector import TxnLike, detect_recurring, detect_all
from app.enums import Cadence


def monthly_series(start: date, amount: float, count: int, day_jitter=0):
    out = []
    d = start
    for i in range(count):
        out.append(TxnLike(txn_date=d + timedelta(days=day_jitter if i % 2 else -day_jitter), amount=amount))
        month = d.month + 1
        year = d.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        d = date(year, month, min(d.day, 28))
    return out


class TestRecurringDetector(unittest.TestCase):
    def test_detects_clean_monthly_subscription(self):
        txns = monthly_series(date(2026, 1, 15), 15.99, 6)
        results = detect_recurring("Netflix", txns)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].cadence, Cadence.MONTHLY.value)
        self.assertAlmostEqual(results[0].amount, 15.99)
        self.assertGreater(results[0].confidence, 0.5)

    def test_annualized_cost_for_monthly(self):
        txns = monthly_series(date(2026, 1, 1), 20.0, 4)
        results = detect_recurring("Openai", txns)
        self.assertAlmostEqual(results[0].annualized_cost, 240.0)

    def test_does_not_flag_single_purchase(self):
        txns = [TxnLike(txn_date=date(2026, 3, 4), amount=52.10)]
        results = detect_recurring("One Off Store", txns)
        self.assertEqual(results, [])

    def test_does_not_flag_random_varying_purchases(self):
        # Same "merchant" (e.g. Amazon) but random dates/amounts - normal
        # shopping, not a subscription. Two occurrences with mismatched
        # amounts and no regular interval should NOT be called recurring.
        txns = [
            TxnLike(txn_date=date(2026, 1, 3), amount=42.10),
            TxnLike(txn_date=date(2026, 1, 19), amount=118.55),
            TxnLike(txn_date=date(2026, 3, 2), amount=9.99),
        ]
        results = detect_recurring("Amazon", txns)
        self.assertEqual(results, [])

    def test_detects_quarterly_cadence(self):
        base = date(2025, 8, 2)
        txns = [
            TxnLike(txn_date=base, amount=51.0),
            TxnLike(txn_date=base + timedelta(days=91), amount=51.0),
            TxnLike(txn_date=base + timedelta(days=182), amount=51.0),
            TxnLike(txn_date=base + timedelta(days=273), amount=51.0),
        ]
        results = detect_recurring("Nyt Digital Subscription", txns)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].cadence, Cadence.QUARTERLY.value)

    def test_amount_tolerance_allows_small_price_variance(self):
        # Same subscription, a couple of charges include a small local tax bump
        txns = [
            TxnLike(txn_date=date(2026, 1, 10), amount=24.99),
            TxnLike(txn_date=date(2026, 2, 10), amount=24.99),
            TxnLike(txn_date=date(2026, 3, 12), amount=25.50),  # +2% - within tolerance
        ]
        results = detect_recurring("Planet Fitness", txns)
        self.assertEqual(len(results), 1)

    def test_detect_all_sorts_by_annualized_cost_descending(self):
        by_merchant = {
            "Netflix": monthly_series(date(2026, 1, 1), 15.99, 4),
            "Geico Insurance": monthly_series(date(2026, 1, 1), 142.00, 4),
            "Spotify": monthly_series(date(2026, 1, 1), 11.99, 4),
        }
        results = detect_all(by_merchant)
        self.assertEqual([r.merchant_normalized for r in results], ["Geico Insurance", "Netflix", "Spotify"])


if __name__ == "__main__":
    unittest.main()
