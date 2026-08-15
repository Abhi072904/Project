"""
Mock insight provider.

Rule-based stand-in for VertexAIProvider. Same interface, same output shape,
zero network calls - this is what actually powers the local demo, since the
environment this was built in can't reach the real Vertex AI API. The rules
here deliberately mirror the instructions in vertex_ai_provider.py's system
prompt, so swapping providers changes *quality and phrasing variety*, not
the categories of insight a user sees.
"""
from app.insights.provider import (
    InsightProvider,
    SpendingContext,
    GeneratedInsight,
    InsightBatch,
)

UNUSED_THRESHOLD_DAYS = 45


class MockProvider(InsightProvider):
    name = "mock"

    def generate_insights(self, context: SpendingContext) -> InsightBatch:
        insights: list[GeneratedInsight] = []

        # 1. Flag unused subscriptions, ranked by cost
        unused = [
            s for s in context.subscriptions
            if s.days_since_last_use is not None and s.days_since_last_use >= UNUSED_THRESHOLD_DAYS
        ]
        for s in sorted(unused, key=lambda s: s.annualized_cost, reverse=True)[:3]:
            insights.append(
                GeneratedInsight(
                    insight_type="unused_subscription",
                    headline=f"{s.display_name} hasn't been touched in {s.days_since_last_use} days",
                    body=(
                        f"You're paying ${s.amount:.2f}/{s.cadence} (${s.annualized_cost:.2f}/yr) "
                        f"for {s.display_name}, last used {s.days_since_last_use} days ago. "
                        f"Cancelling frees up ${s.amount:.2f}/{s.cadence} immediately."
                    ),
                    potential_monthly_savings=round(s.amount if s.cadence == "monthly" else s.annualized_cost / 12, 2),
                    subscription_name=s.display_name,
                )
            )

        # 2. Trend vs prior period
        if context.total_monthly_recurring_prior_period is not None:
            delta = context.total_monthly_recurring - context.total_monthly_recurring_prior_period
            if abs(delta) >= 3:
                pct = (delta / context.total_monthly_recurring_prior_period * 100) if context.total_monthly_recurring_prior_period else 0
                direction = "up" if delta > 0 else "down"
                insights.append(
                    GeneratedInsight(
                        insight_type="trend",
                        headline=f"Recurring spend is {direction} {abs(pct):.0f}% vs last period",
                        body=(
                            f"Monthly recurring charges moved from ${context.total_monthly_recurring_prior_period:.2f} "
                            f"to ${context.total_monthly_recurring:.2f} ({delta:+.2f})."
                        ),
                        potential_monthly_savings=max(0.0, delta),
                    )
                )

        # 3. Category concentration - call out the single biggest category.
        # Requires >=2 categories: with only one category present, "100% of
        # spend" is a trivial artifact of sample size, not a real signal.
        if len(context.spend_by_category) >= 2:
            top_category, top_amount = max(context.spend_by_category.items(), key=lambda kv: kv[1])
            total = sum(context.spend_by_category.values()) or 1
            share = top_amount / total * 100
            if share >= 30:
                insights.append(
                    GeneratedInsight(
                        insight_type="anomaly",
                        headline=f"{top_category} is {share:.0f}% of your recurring spend",
                        body=(
                            f"${top_amount:.2f} of your ${total:.2f} in recurring charges goes to "
                            f"{top_category} alone - worth a closer look if that's more than you'd guess."
                        ),
                    )
                )

        # 4. Fallback: encouraging summary if nothing else fired
        if not insights:
            insights.append(
                GeneratedInsight(
                    insight_type="summary",
                    headline="No red flags this period",
                    body=(
                        f"Your ${context.total_monthly_recurring:.2f}/mo in recurring charges all show "
                        f"recent activity. Nothing worth cutting right now."
                    ),
                )
            )

        return InsightBatch(insights=insights[:5], provider_name=self.name)
