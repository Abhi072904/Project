"""
CSV ingestion for bank/credit-card statement exports.

Accepts the common export shape most banks use: date, description, amount
(sometimes signed, sometimes split into debit/credit columns). This is the
"bronze layer" of the pipeline - raw rows in, normalized+categorized rows out.
The same normalize/categorize logic here is what the AWS Glue job (see
etl/glue_job_transaction_etl.py) runs at batch scale in production; this
module is the row-level unit the Glue job calls per-partition.
"""
from dataclasses import dataclass
from datetime import date, datetime
import csv
import io

from app.ingestion.categorizer import process_merchant

_DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y"]


@dataclass
class ParsedTransaction:
    txn_date: date
    merchant_raw: str
    merchant_normalized: str
    amount: float
    category: str
    account: str | None


class CSVParseError(ValueError):
    pass


def _parse_date(value: str) -> date:
    value = value.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise CSVParseError(f"Unrecognized date format: {value!r}")


def _parse_amount(row: dict) -> float:
    """Handle both a single signed 'amount' column and split debit/credit columns."""
    if "amount" in row and row["amount"]:
        val = row["amount"].replace("$", "").replace(",", "").strip()
        amt = float(val)
        # Bank exports vary: some show spending as negative, some as positive.
        # We normalize to "positive = money out" since that's what a subscription
        # audit cares about; a large positive inflow (paycheck) will simply not
        # match any recurring *charge* pattern later, so sign ambiguity here is safe.
        return abs(amt)
    debit = row.get("debit", "").replace("$", "").replace(",", "").strip()
    if debit:
        return abs(float(debit))
    credit = row.get("credit", "").replace("$", "").replace(",", "").strip()
    if credit:
        return abs(float(credit))
    raise CSVParseError(f"No amount/debit/credit column found in row: {row}")


def parse_transactions_csv(file_content: bytes, account_label: str | None = None) -> list[ParsedTransaction]:
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

    date_col = next((c for c in reader.fieldnames if c in ("date", "transaction date", "posted date")), None)
    desc_col = next((c for c in reader.fieldnames if c in ("description", "merchant", "name")), None)
    if not date_col or not desc_col:
        raise CSVParseError(
            f"CSV must have a date column and a description/merchant column. Found: {reader.fieldnames}"
        )

    results: list[ParsedTransaction] = []
    for i, row in enumerate(reader):
        row = {k.strip().lower(): (v or "") for k, v in row.items()}
        try:
            txn_date = _parse_date(row[date_col])
            merchant_raw = row[desc_col].strip()
            amount = _parse_amount(row)
        except (CSVParseError, ValueError) as e:
            raise CSVParseError(f"Row {i + 2}: {e}") from e

        if not merchant_raw or amount == 0:
            continue

        merchant = process_merchant(merchant_raw)
        results.append(
            ParsedTransaction(
                txn_date=txn_date,
                merchant_raw=merchant_raw,
                merchant_normalized=merchant.normalized,
                amount=round(amount, 2),
                category=merchant.category,
                account=account_label,
            )
        )
    return results
