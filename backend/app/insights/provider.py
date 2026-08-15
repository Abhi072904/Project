"""
Insight provider interface.

SubSense's GenAI layer is behind an interface on purpose: the same
`SpendingContext` gets handed to either a free deterministic MockProvider
(used in local dev / this demo, since the sandbox this was built in has no
outbound network access) or the real VertexAIProvider (used in production,
see insights/vertex_ai_provider.py). Swapping providers is a one-line change
in config.py - nothing in the routers or detection layer needs to know which
one is active. This mirrors the same pattern used for the Claude/OpenAI
provider swap behind Pfizer's patient-matching REST API.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SubscriptionSummary:
    display_name: str
    amount: float
    cadence: str
    annualized_cost: float
    category: str
    days_since_last_use: int | None  # None = user has never logged a "last used" date


@dataclass
class SpendingContext:
    """Everything an insight generator needs to reason about a user's spend."""
    subscriptions: list[SubscriptionSummary]
    total_monthly_recurring: float
    total_monthly_recurring_prior_period: float | None
    spend_by_category: dict[str, float]
    period_label: str = "this month"


@dataclass
class GeneratedInsight:
    insight_type: str  # "unused_subscription" | "trend" | "anomaly" | "summary"
    headline: str
    body: str
    potential_monthly_savings: float = 0.0
    subscription_name: str | None = None


@dataclass
class InsightBatch:
    insights: list[GeneratedInsight] = field(default_factory=list)
    provider_name: str = "unknown"


class InsightProvider(ABC):
    """Implement this to plug a new model/provider into SubSense."""

    name: str = "base"

    @abstractmethod
    def generate_insights(self, context: SpendingContext) -> InsightBatch:
        """Return a batch of natural-language insights for the given spending context."""
        raise NotImplementedError
