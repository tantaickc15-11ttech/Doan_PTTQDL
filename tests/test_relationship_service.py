"""Tests for correlation evidence used in EDA."""

import unittest

import pandas as pd

from src.services.relationship_service import RelationshipService


class RelationshipServiceTests(unittest.TestCase):
    def test_high_level_alerts_is_available_as_a_correlation_target(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 4,
                "high_level_alerts": [1, 2, 3, 4],
                "total_events": [5, 8, 11, 14],
            }
        )

        result = RelationshipService.correlation_with(
            summary, "high_level_alerts"
        )

        self.assertIn("high_level_alerts", RelationshipService.NUMERIC_METRICS)
        self.assertIn("total_events", result["variable"].tolist())
        self.assertAlmostEqual(
            1.0,
            result.loc[
                result["variable"] == "total_events", "correlation"
            ].iloc[0],
        )
        self.assertTrue(
            bool(
                result.loc[
                    result["variable"] == "total_events", "selected"
                ].iloc[0]
            )
        )

    def test_correlation_marks_strong_numeric_relationship(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 4,
                "total_events": [1, 2, 3, 4],
                "high_level_alerts": [2, 4, 6, 8],
                "unique_rules": [1, 1, 2, 2],
            }
        )
        result = RelationshipService.correlation_with(summary, "total_events")
        row = result[result["variable"] == "high_level_alerts"].iloc[0]
        self.assertAlmostEqual(1.0, row["correlation"])
        self.assertLess(row["p_value"], 0.001)
        self.assertIn("Mạnh - Đồng thuận", row["conclusion"])
        self.assertIn("bằng chứng rất mạnh", row["conclusion"])

    def test_correlation_table_keeps_constant_numeric_columns(self):
        summary = pd.DataFrame(
            {
                "high_level_alerts": [10, 20, 30, 40],
                "total_events": [1, 2, 3, 4],
                "unique_rules": [1, 1, 1, 1],
            }
        )

        result = RelationshipService.correlation_with(
            summary, "high_level_alerts"
        )
        constant = result[result["variable"] == "unique_rules"].iloc[0]

        self.assertTrue(pd.isna(constant["p_value"]))
        self.assertFalse(bool(constant["selected"]))

    def test_correlation_uses_only_columns_in_the_processed_dataset(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 4,
                "event_date": pd.date_range("2026-10-01", periods=4, tz="UTC"),
                "high_level_alerts": [10, 20, 30, 40],
                "total_events": [1, 2, 3, 4],
                "level_11_plus_alerts": [0, 1, 2, 3],
            }
        )

        result = RelationshipService.correlation_with(
            summary, "high_level_alerts"
        )

        self.assertNotIn("level_11_plus_alerts", result["variable"].tolist())
        self.assertNotIn("agent_name", result["variable"].tolist())
        self.assertNotIn("event_date", result["variable"].tolist())

    def test_correlation_uses_course_strength_and_direction_thresholds(self):
        self.assertEqual(
            "Mạnh - Không đồng thuận (nghịch chiều)",
            RelationshipService.classify_correlation(-0.85),
        )
        self.assertEqual(
            "Vừa - Đồng thuận",
            RelationshipService.classify_correlation(0.65),
        )
        self.assertEqual(
            "Yếu - Đồng thuận",
            RelationshipService.classify_correlation(0.35),
        )
        self.assertEqual(
            "Không tương quan đáng kể",
            RelationshipService.classify_correlation(-0.20),
        )
        self.assertIn("rất mạnh", RelationshipService.classify_p_value(0.0001))
        self.assertIn("bằng chứng vừa", RelationshipService.classify_p_value(0.01))
        self.assertIn("bằng chứng yếu", RelationshipService.classify_p_value(0.08))
        self.assertIn("chưa có", RelationshipService.classify_p_value(0.20))

    def test_anova_concludes_from_p_value(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 5 + ["B"] * 5,
                "total_events": [8, 9, 10, 11, 12, 18, 19, 20, 21, 22],
            }
        )
        result = RelationshipService.anova_by_agent(summary, "total_events")
        self.assertTrue(result["available"])
        self.assertEqual(2, result["groups"])
        self.assertLess(result["p_value"], 0.05)
        self.assertIn("chọn biến agent_name", result["conclusion"])
        self.assertNotIn("normality_ok", result)
        self.assertNotIn("equal_variance_ok", result)
        self.assertNotIn("levene_p_value", result)

    def test_anova_defaults_to_total_events(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 5 + ["B"] * 5,
                "total_events": [8, 9, 10, 11, 12, 80, 90, 100, 110, 120],
            }
        )

        result = RelationshipService.anova_by_agent(summary)

        self.assertTrue(result["available"])
        self.assertLess(result["p_value"], 0.05)


if __name__ == "__main__":
    unittest.main()
