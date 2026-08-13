import unittest
from datetime import date

from app.ingestion.csv_parser import parse_transactions_csv, CSVParseError


class TestCsvParser(unittest.TestCase):
    def test_parses_basic_csv(self):
        content = b"date,description,amount\n2026-01-15,NETFLIX.COM 866-579-7172,15.99\n"
        results = parse_transactions_csv(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].txn_date, date(2026, 1, 15))
        self.assertEqual(results[0].merchant_normalized, "Netflix")
        self.assertEqual(results[0].amount, 15.99)
        self.assertEqual(results[0].category, "Streaming")

    def test_handles_mm_dd_yyyy_dates(self):
        content = b"date,description,amount\n01/15/2026,SPOTIFY USA,11.99\n"
        results = parse_transactions_csv(content)
        self.assertEqual(results[0].txn_date, date(2026, 1, 15))

    def test_handles_debit_credit_columns_instead_of_amount(self):
        content = b"date,description,debit,credit\n2026-01-15,SHELL OIL 4471,45.20,\n"
        results = parse_transactions_csv(content)
        self.assertEqual(results[0].amount, 45.20)

    def test_skips_zero_amount_rows(self):
        content = b"date,description,amount\n2026-01-15,PENDING AUTH,0.00\n2026-01-16,NETFLIX.COM,15.99\n"
        results = parse_transactions_csv(content)
        self.assertEqual(len(results), 1)

    def test_raises_on_missing_required_columns(self):
        content = b"transaction_id,merchant_name\n1,Netflix\n"
        with self.assertRaises(CSVParseError):
            parse_transactions_csv(content)

    def test_raises_with_row_number_on_bad_date(self):
        content = b"date,description,amount\n2026-01-15,NETFLIX,15.99\nNOT-A-DATE,SPOTIFY,11.99\n"
        with self.assertRaises(CSVParseError) as ctx:
            parse_transactions_csv(content)
        self.assertIn("Row 3", str(ctx.exception))

    def test_strips_dollar_signs_and_commas_in_amount(self):
        content = b"date,description,amount\n2026-01-15,GEICO INSURANCE,\"$1,142.00\"\n"
        results = parse_transactions_csv(content)
        self.assertEqual(results[0].amount, 1142.00)


if __name__ == "__main__":
    unittest.main()
