"""
Generates sample_transactions.csv - synthetic demo data, not real financial data.

Kept in the repo (rather than just shipping the CSV) so it's obvious exactly
how the demo dataset was built and why certain subscriptions show up flagged.
Run: python generate_sample_data.py
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)  # deterministic output

START = date(2025, 7, 10)
END = date(2026, 8, 13)  # "today" in this project's build environment

rows: list[tuple[date, str, float]] = []


def monthly(merchant: str, base_amount: float, day_of_month: int, jitter_days: int = 2, jitter_amt: float = 0.0):
    d = date(START.year, START.month, min(day_of_month, 28))
    while d <= END:
        amt = base_amount + random.uniform(-jitter_amt, jitter_amt)
        actual_day = d + timedelta(days=random.randint(-jitter_days, jitter_days))
        rows.append((actual_day, merchant, round(amt, 2)))
        month = d.month + 1
        year = d.year + (1 if month > 12 else 0)
        month = 1 if month > 12 else month
        d = date(year, month, min(day_of_month, 28))


def periodic(merchant: str, amount: float, start: date, interval_days: int, jitter_days: int = 3):
    d = start
    while d <= END:
        actual_day = d + timedelta(days=random.randint(-jitter_days, jitter_days))
        rows.append((actual_day, merchant, amount))
        d = d + timedelta(days=interval_days)


# ---- Recurring subscriptions ----
monthly("NETFLIX.COM 866-579-7172", 15.99, 28, jitter_days=1)
monthly("SPOTIFY USA", 11.99, 5, jitter_days=1)
monthly("SQ *PLANET FITNESS #4021", 24.99, 10, jitter_days=1)          # -> will be flagged (unused override)
monthly("PP*PELOTON INTERAKTIV", 44.00, 15, jitter_days=1)             # -> will be flagged (unused override)
monthly("OPENAI CHATGPT SUBSCRIPTION", 20.00, 22, jitter_days=1)
monthly("ADOBE CREATIVE CLOUD", 54.99, 18, jitter_days=1)
monthly("GEICO INSURANCE", 142.00, 3, jitter_days=1, jitter_amt=0.0)
periodic("NYT DIGITAL SUBSCRIPTION", 51.00, date(2025, 8, 2), 91, jitter_days=3)
periodic("AMAZON PRIME MEMBERSHIP", 139.00, date(2024, 8, 5), 365, jitter_days=2)  # 3 yearly charges -> meets MIN_OCCURRENCES

# ---- Non-recurring noise: groceries, gas, dining, one-off shopping, rideshare ----
groceries = ["WHOLE FOODS MKT", "TRADER JOE'S #142", "WEGMANS #33", "SAFEWAY #221"]
gas = ["SHELL OIL 57443921", "EXXON MOBIL 88213", "CHEVRON 00219"]
dining = ["CHIPOTLE 2214", "SWEETGREEN DTLA", "STARBUCKS #4471", "LOCAL COFFEE CO", "PANERA BREAD #88"]
rideshare = ["UBER *TRIP HELP.UBER.COM", "LYFT *RIDE THU"]
shopping = ["AMAZON.COM*A1B2C3", "TARGET 00034821", "WALMART.COM", "COSTCO WHSE #221"]

d = START
while d <= END:
    if random.random() < 0.55:
        rows.append((d, random.choice(groceries), round(random.uniform(28, 145), 2)))
    if random.random() < 0.25:
        rows.append((d, random.choice(gas), round(random.uniform(32, 68), 2)))
    if random.random() < 0.35:
        rows.append((d, random.choice(dining), round(random.uniform(9, 42), 2)))
    if random.random() < 0.15:
        rows.append((d, random.choice(rideshare), round(random.uniform(11, 34), 2)))
    if random.random() < 0.10:
        rows.append((d, random.choice(shopping), round(random.uniform(15, 220), 2)))
    d += timedelta(days=1)

rows.sort(key=lambda r: r[0])

with open("sample_transactions.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["date", "description", "amount"])
    for txn_date, merchant, amount in rows:
        writer.writerow([txn_date.isoformat(), merchant, f"{amount:.2f}"])

print(f"Wrote {len(rows)} transactions to sample_transactions.csv ({START} to {END})")
