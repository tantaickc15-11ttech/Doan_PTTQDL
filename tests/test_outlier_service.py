"""Tests for the documented IQR outlier calculation."""

import unittest

import pandas as pd

from src.services.outlier_service import OutlierService


class OutlierServiceTests(unittest.TestCase):
    def test_iqr_detects_large_agent_day_value(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 5,
                "event_date": pd.date_range("2026-10-01", periods=5, tz="UTC"),
                "level_0_7_events": [10, 11, 9, 10, 100],
                "level_8_10_events": [3, 2, 4, 3, 2],
                "level_above_10_events": [0, 1, 0, 1, 0],
            }
        )
        result = OutlierService.analyze(summary, "Event Level 0-7")
        self.assertEqual(1, result["outlier_count"])
        self.assertEqual(100, result["outliers"].iloc[0]["value"])
        self.assertAlmostEqual(10, result["q1"])
        self.assertAlmostEqual(10, result["q2"])
        self.assertAlmostEqual(11, result["q3"])
        self.assertAlmostEqual(8.5, result["lower_bound"])
        self.assertAlmostEqual(12.5, result["upper_bound"])
        self.assertGreater(result["skewness"], 0.5)
        self.assertIn("Lệch phải", result["skew_conclusion"])
        self.assertGreater(result["kurtosis"], 0.5)
        self.assertIn("nhọn", result["kurtosis_conclusion"])
        self.assertEqual(200, len(result["density_x"]))
        self.assertEqual(200, len(result["density_y"]))

        summary_with_total = summary.assign(total_events=[13, 14, 13, 14, 102])
        all_results = OutlierService.analyze_selection(
            summary_with_total, "Tất cả"
        )
        self.assertEqual(1, len(all_results))
        self.assertEqual("total_events", all_results[0]["metric"])
        total_result = OutlierService.analyze_total(summary_with_total)
        self.assertEqual("Tất cả Event", total_result["label"])
        self.assertEqual(156, int(total_result["values"].sum()))

    def test_daily_total_events_is_analyzed_separately_for_each_agent(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 5 + ["B"] * 5,
                "event_date": pd.date_range(
                    "2026-10-01", periods=5, tz="UTC"
                ).tolist() * 2,
                "total_events": [10, 10, 11, 12, 100, 200, 210, 220, 230, 240],
            }
        )

        results = OutlierService.analyze_total_events_by_agent(summary)

        self.assertEqual(["A", "B"], [result["agent_name"] for result in results])
        self.assertEqual(1, results[0]["outlier_count"])
        self.assertEqual(0, results[1]["outlier_count"])
        self.assertAlmostEqual(11, results[0]["q2"])
        self.assertAlmostEqual(220, results[1]["q2"])
        self.assertNotEqual(results[0]["upper_bound"], results[1]["upper_bound"])

    def test_total_events_lower_bound_keeps_the_raw_iqr_result(self):
        summary = pd.DataFrame(
            {
                "agent_name": ["A"] * 4,
                "event_date": pd.date_range("2026-10-01", periods=4, tz="UTC"),
                "total_events": [0, 0, 100, 200],
            }
        )

        result = OutlierService.analyze_total_events_by_agent(summary)[0]

        self.assertEqual(-187.5, result["lower_bound"])



if __name__ == "__main__":
    unittest.main()
