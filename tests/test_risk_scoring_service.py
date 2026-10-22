"""Tests for the documented Agent risk-index scoring rule."""

import unittest

import pandas as pd

from src.services.risk_scoring_service import RiskScoringService


class RiskScoringServiceTests(unittest.TestCase):
    def test_event_scores_follow_the_four_level_bands(self):
        levels = pd.Series([0, 7, 8, 10, 11, 12, 13, 15])
        observed = RiskScoringService.event_scores(levels).tolist()
        self.assertEqual([1, 1, 4, 4, 16, 16, 64, 64], observed)

    def test_classification_uses_level_bands(self):
        cases = {
            0: "Low", 7: "Low", 8: "Medium", 10: "Medium",
            11: "High", 12: "High", 13: "Critical", 15: "Critical",
        }
        for level, expected in cases.items():
            with self.subTest(level=level):
                self.assertEqual(expected, RiskScoringService.classify_level(level))

    def test_daily_index_can_sum_without_an_upper_limit(self):
        low_total = RiskScoringService.event_scores(pd.Series([7] * 100)).sum()
        critical_total = RiskScoringService.event_scores(pd.Series([13] * 5)).sum()
        self.assertEqual(100, low_total)
        self.assertEqual(320, critical_total)
        self.assertGreater(critical_total, low_total)


if __name__ == "__main__":
    unittest.main()
