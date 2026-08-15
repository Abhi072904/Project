import unittest

from app.insights.mock_provider import MockProvider
from app.insights.provider import SpendingContext, SubscriptionSummary


class TestMockProvider(unittest.TestCase):
    def setUp(self):
        self.provider = MockProvider()

    def test_flags_unused_subscription(self):
        context = SpendingContext(
            subscriptions=[
                SubscriptionSummary("Peloton Interaktiv", 44.0, "monthly", 528.0, "Fitness & Health", 103),
            ],
            total_monthly_recurring=44.0,
            total_monthly_recurring_prior_period=None,
            spend_by_category={"Fitness & Health": 44.0},
        )
        batch = self.provider.generate_insights(context)
        self.assertTrue(any(i.insight_type == "unused_subscription" for i in batch.insights))
        unused = next(i for i in batch.insights if i.insight_type == "unused_subscription")
        self.assertIn("Peloton", unused.headline)
        self.assertEqual(unused.potential_monthly_savings, 44.0)

    def test_does_not_flag_recently_used_subscription(self):
        context = SpendingContext(
            subscriptions=[
                SubscriptionSummary("Netflix", 15.99, "monthly", 191.88, "Streaming", 3),
            ],
            total_monthly_recurring=15.99,
            total_monthly_recurring_prior_period=None,
            spend_by_category={"Streaming": 15.99},
        )
        batch = self.provider.generate_insights(context)
        self.assertFalse(any(i.insight_type == "unused_subscription" for i in batch.insights))

    def test_falls_back_to_summary_when_nothing_stands_out(self):
        context = SpendingContext(
            subscriptions=[SubscriptionSummary("Netflix", 15.99, "monthly", 191.88, "Streaming", 2)],
            total_monthly_recurring=15.99,
            total_monthly_recurring_prior_period=None,
            spend_by_category={"Streaming": 15.99},
        )
        batch = self.provider.generate_insights(context)
        self.assertEqual(len(batch.insights), 1)
        self.assertEqual(batch.insights[0].insight_type, "summary")

    def test_caps_at_five_insights(self):
        subs = [
            SubscriptionSummary(f"Service {i}", 20.0, "monthly", 240.0, "Software & AI", 200)
            for i in range(10)
        ]
        context = SpendingContext(
            subscriptions=subs,
            total_monthly_recurring=200.0,
            total_monthly_recurring_prior_period=None,
            spend_by_category={"Software & AI": 200.0},
        )
        batch = self.provider.generate_insights(context)
        self.assertLessEqual(len(batch.insights), 5)


if __name__ == "__main__":
    unittest.main()
