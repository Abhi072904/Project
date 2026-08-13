from enum import Enum


class Cadence(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    IRREGULAR = "irregular"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"          # still charging, not yet reviewed
    REVIEWED = "reviewed"      # user looked at it and chose to keep it (stamped "audited")
    FLAGGED = "flagged"        # detector thinks it's worth cutting (unused 45+ days)
    CANCELLED = "cancelled"    # user marked it cancelled -> counted as realized savings
