import unittest
from datetime import date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from return_rules import return_eligibility


class ReturnRulesTests(unittest.TestCase):
    def test_tier_boundaries_and_future_dates(self):
        today = date(2026, 11, 6)
        self.assertTrue(return_eligibility('Standard', '2026-10-07', today))
        self.assertFalse(return_eligibility('Standard', '2026-10-06', today))
        self.assertTrue(return_eligibility('Premium', '2026-09-07', today))
        self.assertFalse(return_eligibility('Premium', '2026-09-06', today))
        self.assertFalse(return_eligibility('Premium', '2026-11-07', today))

    def test_unknown_tier_or_invalid_date_fails_closed(self):
        self.assertFalse(return_eligibility('Unknown', '2026-11-01', date(2026, 11, 6)))
        self.assertFalse(return_eligibility('Premium', 'not-a-date', date(2026, 11, 6)))


if __name__ == '__main__':
    unittest.main()
