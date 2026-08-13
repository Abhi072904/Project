import unittest

from app.ingestion.categorizer import normalize_merchant, categorize, process_merchant


class TestNormalizeMerchant(unittest.TestCase):
    def test_strips_square_prefix(self):
        self.assertEqual(normalize_merchant("SQ *PLANET FITNESS #4021"), "Planet Fitness")

    def test_strips_paypal_prefix(self):
        self.assertEqual(normalize_merchant("PP*PELOTON INTERAKTIV"), "Peloton Interaktiv")

    def test_strips_phone_number_suffix(self):
        self.assertEqual(normalize_merchant("NETFLIX.COM 866-579-7172"), "Netflix")

    def test_strips_dot_com(self):
        self.assertEqual(normalize_merchant("HELLOFRESH.COM"), "Hellofresh")

    def test_handles_plain_name(self):
        self.assertEqual(normalize_merchant("Spotify Usa"), "Spotify Usa")

    def test_two_different_raw_strings_normalize_to_same_key(self):
        # This is the whole point: statement noise varies charge to charge,
        # but the recurring detector needs a stable key to group on.
        a = normalize_merchant("NETFLIX.COM 866-579-7172")
        b = normalize_merchant("netflix.com")
        self.assertEqual(a, b)


class TestCategorize(unittest.TestCase):
    def test_streaming_keyword_match(self):
        category, confidence = categorize("Netflix")
        self.assertEqual(category, "Streaming")
        self.assertGreater(confidence, 0.9)

    def test_fitness_keyword_match(self):
        category, _ = categorize("Planet Fitness")
        self.assertEqual(category, "Fitness & Health")

    def test_unknown_merchant_falls_back_to_other(self):
        category, confidence = categorize("Bob'S Local Hardware Store")
        self.assertEqual(category, "Other")
        self.assertLess(confidence, 0.5)


class TestProcessMerchant(unittest.TestCase):
    def test_full_pipeline(self):
        result = process_merchant("SQ *PLANET FITNESS #4021")
        self.assertEqual(result.normalized, "Planet Fitness")
        self.assertEqual(result.category, "Fitness & Health")
        self.assertGreater(result.category_confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
