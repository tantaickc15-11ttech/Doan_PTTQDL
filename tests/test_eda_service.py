"""Tests for filtering and descriptive EDA calculations."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.services.eda_service import EdaService


class EdaServiceTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame(
            {
                "timestamp_utc": pd.to_datetime(
                    [
                        "2026-10-01T00:00:00Z",
                        "2026-10-02T00:00:00Z",
                        "2026-10-05T00:00:00Z",
                    ],
                    utc=True,
                ),
                "agent_name": ["A", "A", "B"],
                "rule_id": pd.Series(["1", "2", "1"], dtype="string"),
                "rule_level": pd.Series([7, 10, 13], dtype="Int64"),
                "rule_firedtimes": pd.Series([1, 2, 3], dtype="Int64"),
                "event_id": pd.Series(["100", None, "200"], dtype="string"),
                "source_ip": pd.Series(["10.0.0.1", None, None], dtype="string"),
                "dst_user": pd.Series([None, None, "bob"], dtype="string"),
                "src_ip": pd.Series([None, "10.0.0.2", None], dtype="string"),
                "target_user_name": pd.Series(["alice", None, None], dtype="string"),
                "rule_description": pd.Series(["One", "Two", "One"], dtype="string"),
            }
        )
        self.frame["analysis_source_ip"] = self.frame["source_ip"].fillna(
            self.frame["src_ip"]
        )
        self.frame["analysis_user"] = self.frame["target_user_name"].fillna(
            self.frame["dst_user"]
        )
        self.frame["event_date"] = self.frame["timestamp_utc"].dt.floor("D")

    def test_filter_uses_latest_dataset_timestamp(self):
        filtered, details = EdaService.filter_data(self.frame, agent="B", days=3)
        self.assertEqual(1, len(filtered))
        self.assertEqual("B", filtered.iloc[0]["agent_name"])
        self.assertEqual(pd.Timestamp("2026-10-05T00:00:00Z"), filtered.iloc[0]["timestamp_utc"])
        self.assertEqual(pd.Timestamp("2026-10-03T00:00:00Z"), details["filter_start"])

    def test_overview_combines_ip_and_user_fields(self):
        overview = EdaService.overview(self.frame)
        self.assertEqual(3, overview["total_alerts"])
        self.assertEqual(2, overview["unique_source_ips"])
        self.assertEqual(2, overview["unique_users"])

    def test_filter_by_alert_level(self):
        filtered, details = EdaService.filter_data(
            self.frame, agent="Tất cả", days=30, alert_level="10"
        )
        self.assertEqual(1, len(filtered))
        self.assertEqual(10, filtered.iloc[0]["rule_level"])
        self.assertEqual("10", details["selected_alert_level"])

    def test_filter_by_one_specific_utc_date(self):
        filtered, details = EdaService.filter_data(
            self.frame,
            agent="Tất cả",
            days=30,
            alert_level="Tất cả",
            specific_date="2026-10-02",
        )

        self.assertEqual(1, len(filtered))
        self.assertEqual(
            pd.Timestamp("2026-10-02T00:00:00Z"),
            filtered.iloc[0]["timestamp_utc"],
        )
        self.assertEqual("specific_date", details["filter_mode"])
        self.assertEqual("2026-10-02", details["selected_date"])

    def test_filter_by_inclusive_date_range(self):
        filtered, details = EdaService.filter_data(
            self.frame,
            start_date="2026-10-01",
            end_date="2026-10-02",
        )

        self.assertEqual(2, len(filtered))
        self.assertEqual("date_range", details["filter_mode"])
        self.assertEqual("2026-10-01", details["selected_start_date"])
        self.assertEqual("2026-10-02", details["selected_end_date"])

    def test_filter_rejects_reversed_date_range(self):
        with self.assertRaisesRegex(ValueError, "Ngày bắt đầu"):
            EdaService.filter_data(
                self.frame,
                start_date="2026-10-05",
                end_date="2026-10-01",
            )

    def test_aggregate_agent_day_includes_zero_alert_days(self):
        filtered, _details = EdaService.filter_data(self.frame, days=3)
        summary = EdaService.aggregate_agent_day(filtered)
        self.assertEqual(3, len(summary))
        self.assertIn(0, summary["total_events"].tolist())
        grouped_total = (
            summary["level_0_7_events"]
            + summary["level_8_10_events"]
            + summary["level_above_10_events"]
        )
        self.assertTrue(grouped_total.equals(summary["total_events"]))

    def test_level_11_plus_alerts_is_daily_count(self):
        summary = EdaService.aggregate_agent_day(self.frame)
        observed = summary[summary["total_events"] > 0]
        empty = summary[summary["total_events"] == 0]

        self.assertEqual([0, 0, 1], observed["level_11_plus_alerts"].tolist())
        self.assertTrue((empty["level_11_plus_alerts"] == 0).all())

    def test_high_level_alerts_counts_from_level_10(self):
        summary = EdaService.aggregate_agent_day(self.frame)
        observed = summary[summary["total_events"] > 0]
        empty = summary[summary["total_events"] == 0]

        self.assertEqual([0, 1, 1], observed["high_level_alerts"].tolist())
        self.assertTrue((empty["high_level_alerts"] == 0).all())

    def test_agent_high_level_counts_includes_all_levels_from_10_to_max(self):
        grouped = EdaService.agent_high_level_counts(self.frame, minimum_level=10)

        self.assertEqual([10, 11, 12, 13], grouped.columns.tolist())
        self.assertEqual(1, grouped.loc["A", 10])
        self.assertEqual(1, grouped.loc["B", 13])
        self.assertEqual(0, grouped.loc["A", 11])
        self.assertEqual(2, int(grouped.to_numpy().sum()))

    def test_agent_level_counts_includes_every_observed_level(self):
        grouped = EdaService.agent_level_counts(self.frame)

        self.assertEqual([7, 10, 13], grouped.columns.tolist())
        self.assertEqual(["A", "B"], grouped.index.tolist())
        self.assertEqual(1, grouped.loc["A", 7])
        self.assertEqual(1, grouped.loc["A", 10])
        self.assertEqual(1, grouped.loc["B", 13])
        self.assertEqual(3, int(grouped.to_numpy().sum()))


if __name__ == "__main__":
    unittest.main()
