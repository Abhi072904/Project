"""
Recurring-charge detection.

This is the algorithmic heart of SubSense: given a pile of transactions,
figure out which merchants represent a subscription (same payee, similar
amount, regular interval) versus one-off spending. Deliberately rule-based
and explainable rather than ML-black-box - a user auditing their money should
be able to see *why* something got flagged.

Approach:
  1. Group transactions by normalized merchant.
  2. Within a merchant, cluster by amount (a merchant can run >1 subscription
     at different price points, e.g., two Netflix tiers on shared accounts).
  3. For each amount cluster with >=2 charges, look at the day-gaps between
     consecutive charges and classify the cadence if the gaps are consistent
     enough (allowing real-world jitter: billing dates drift a few days/month).
  4. Score a confidence based on occurrence count + interval consistency.
"""
from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev

from app.enums import Cadence

# (label, expected_days, tolerance_days)
_CADENCE_BANDS = [
    (Cadence.WEEKLY, 7, 2),
    (Cadence.MONTHLY, 30, 5),
    (Cadence.QUARTERLY, 91, 10),
    (Cadence.ANNUAL, 365, 20),
]

MIN_OCCURRENCES = 3  # two points can't establish "consistent interval" at all
AMOUNT_TOLERANCE_PCT = 0.06  # 6% - covers small price bumps / tax variance
MIN_CONFIDENCE = 0.5  # below this, treat it as noise rather than a subscription


@dataclass
class TxnLike:
    txn_date: date
    amount: float


@dataclass
class DetectedSubscription:
    merchant_normalized: str
    amount: float
    cadence: str
    first_seen: date
    last_seen: date
    occurrences: int
    confidence: float
    annualized_cost: float = field(init=False)

    def __post_init__(self):
        multiplier = {
            Cadence.WEEKLY.value: 52,
            Cadence.MONTHLY.value: 12,
            Cadence.QUARTERLY.value: 4,
            Cadence.ANNUAL.value: 1,
            Cadence.IRREGULAR.value: 12,  # conservative fallback
        }[self.cadence]
        self.annualized_cost = round(self.amount * multiplier, 2)


def _cluster_by_amount(txns: list[TxnLike]) -> list[list[TxnLike]]:
    """Group same-merchant transactions into amount clusters within tolerance."""
    clusters: list[list[TxnLike]] = []
    for txn in sorted(txns, key=lambda t: t.amount):
        placed = False
        for cluster in clusters:
            ref = mean(t.amount for t in cluster)
            if abs(txn.amount - ref) <= max(ref * AMOUNT_TOLERANCE_PCT, 0.50):
                cluster.append(txn)
                placed = True
                break
        if not placed:
            clusters.append([txn])
    return clusters


def _classify_cadence(intervals: list[int]) -> tuple[str, float]:
    """Given day-gaps between consecutive charges, pick a cadence + confidence."""
    if not intervals:
        return Cadence.IRREGULAR.value, 0.0

    avg_gap = mean(intervals)
    spread = pstdev(intervals) if len(intervals) > 1 else 0.0

    for cadence, expected, tolerance in _CADENCE_BANDS:
        # Both the average gap AND the spread must fit the band - a pattern
        # like [5, 55, 30] averages to a plausible 30 days but is not
        # remotely consistent billing. Occurrence count is never allowed to
        # compensate for bad timing consistency (that was the bug behind the
        # false-positive "subscriptions" real grocery/gas spending produced).
        if abs(avg_gap - expected) <= tolerance and spread <= tolerance:
            consistency = max(0.0, 1 - (spread / max(tolerance, 1)))
            occurrence_boost = min(1.0, len(intervals) / 4)  # more data points = more trust
            confidence = round(0.5 * consistency + 0.5 * occurrence_boost, 2)
            return cadence.value, min(confidence, 0.99)

    return Cadence.IRREGULAR.value, 0.15


def detect_recurring(
    merchant_normalized: str, txns: list[TxnLike]
) -> list[DetectedSubscription]:
    """Return zero or more DetectedSubscriptions found within one merchant's transactions."""
    if len(txns) < MIN_OCCURRENCES:
        return []

    results: list[DetectedSubscription] = []
    for cluster in _cluster_by_amount(txns):
        if len(cluster) < MIN_OCCURRENCES:
            continue
        ordered = sorted(cluster, key=lambda t: t.txn_date)
        intervals = [
            (ordered[i].txn_date - ordered[i - 1].txn_date).days
            for i in range(1, len(ordered))
        ]
        cadence, confidence = _classify_cadence(intervals)
        if confidence < MIN_CONFIDENCE:
            # A cadence band technically matched, but weakly (borderline avg
            # gap, thin occurrence count, or both). Real subscriptions in
            # practice score well above this line; borderline matches are
            # much more often coincidence in everyday repeat-merchant spend
            # (same coffee shop, same gas station) than a missed subscription.
            continue
        if cadence == Cadence.IRREGULAR.value:
            # By definition a subscription bills on a regular schedule. Everyday
            # spending at a repeat merchant (groceries, gas, coffee) will always
            # rack up 3+ same-merchant charges over months, and some will land
            # within the amount-tolerance band by pure chance - if the interval
            # pattern doesn't fit a real cadence, it's not a subscription, no
            # matter how many occurrences there are.
            continue

        results.append(
            DetectedSubscription(
                merchant_normalized=merchant_normalized,
                amount=round(mean(t.amount for t in ordered), 2),
                cadence=cadence,
                first_seen=ordered[0].txn_date,
                last_seen=ordered[-1].txn_date,
                occurrences=len(ordered),
                confidence=confidence,
            )
        )
    return results


def detect_all(transactions_by_merchant: dict[str, list[TxnLike]]) -> list[DetectedSubscription]:
    """Run detection across every merchant group and flatten the results."""
    found: list[DetectedSubscription] = []
    for merchant, txns in transactions_by_merchant.items():
        found.extend(detect_recurring(merchant, txns))
    return sorted(found, key=lambda s: s.annualized_cost, reverse=True)
