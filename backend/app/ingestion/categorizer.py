"""
Merchant normalization + categorization.

Bank/card statement merchant strings are messy: "SQ *BLUE BOTTLE #4429",
"NETFLIX.COM 866-579-7172", "PAYPAL *SPOTIFY". Before we can detect recurring
charges we have to collapse these variants down to one canonical merchant key.
This is a deliberately rule-based layer (fast, free, deterministic) - the LLM
budget is reserved for the insight-generation step, not for classifying rows.
"""
import re
from dataclasses import dataclass

# Processor/payment-rail prefixes that show up glued to the real merchant name
_NOISE_PREFIXES = [
    r"^SQ \*",
    r"^SP \*",
    r"^PAYPAL \*",
    r"^PP\*",
    r"^TST\*",
    r"^POS DEBIT ",
    r"^ACH DEBIT ",
    r"^DEBIT CARD PURCHASE ",
    r"^RECURRING PAYMENT ",
]
# Trailing noise: phone numbers, store numbers, state codes, transaction ids
_NOISE_SUFFIXES = [
    r"\s+\d{3}-\d{3}-\d{4}$",
    r"\s+#\d+$",
    r"\s+\d{4,}$",
    r"\s+[A-Z]{2}$",
    r"\.COM$",
    r"\*\d+$",
]

# category -> keywords matched against the normalized merchant name
_CATEGORY_RULES: dict[str, list[str]] = {
    "Streaming": ["netflix", "hulu", "disney+", "disney plus", "max", "hbo",
                  "peacock", "paramount", "spotify", "apple music", "youtube premium",
                  "audible", "crunchyroll"],
    "Software & AI": ["openai", "chatgpt", "anthropic", "claude", "adobe",
                       "microsoft 365", "notion", "figma", "github", "dropbox",
                       "icloud", "google one", "1password", "grammarly"],
    "Fitness & Health": ["planet fitness", "equinox", "peloton", "gym", "yoga",
                          "classpass", "whoop", "headspace", "calm"],
    "News & Reading": ["nyt", "new york times", "wsj", "wall street journal",
                        "medium", "kindle unlimited", "audible"],
    "Food Delivery": ["doordash", "grubhub", "uber eats", "instacart", "hellofresh",
                       "blue apron"],
    "Utilities": ["comcast", "xfinity", "verizon", "at&t", "t-mobile", "spectrum",
                   "con edison", "pge", "national grid"],
    "Transport": ["uber", "lyft", "shell", "exxon", "chevron"],
    "Shopping": ["amazon", "walmart", "target", "costco"],
}


@dataclass
class NormalizedMerchant:
    raw: str
    normalized: str
    category: str
    category_confidence: float


def normalize_merchant(raw_name: str) -> str:
    """Collapse a messy statement string down to a canonical merchant key."""
    name = raw_name.strip().upper()
    for pattern in _NOISE_PREFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    for pattern in _NOISE_SUFFIXES:
        name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    # collapse internal whitespace, strip stray punctuation
    name = re.sub(r"[^\w\s&+]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else raw_name.strip().title()


def categorize(normalized_name: str) -> tuple[str, float]:
    """Return (category, confidence) for an already-normalized merchant name."""
    lowered = normalized_name.lower()
    for category, keywords in _CATEGORY_RULES.items():
        for kw in keywords:
            if kw in lowered:
                return category, 0.95
    return "Other", 0.3


def process_merchant(raw_name: str) -> NormalizedMerchant:
    normalized = normalize_merchant(raw_name)
    category, confidence = categorize(normalized)
    return NormalizedMerchant(
        raw=raw_name,
        normalized=normalized,
        category=category,
        category_confidence=confidence,
    )
