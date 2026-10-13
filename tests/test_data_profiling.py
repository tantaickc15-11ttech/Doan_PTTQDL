"""Kiểm thử báo cáo baseline trước cleaning."""

import json
import tempfile
import unittest
from pathlib import Path

from src.services.data_profiling_service import DataProfilingService


class DataProfilingServiceTests(unittest.TestCase):
    def test_profile_counts_quality_without_cleaning(self):
        records = [
            {
                "id": "a-1",
                "timestamp": "2026-10-01T00:00:00+0000",
                "agent": {"id": "001", "name": "PC-01"},
                "rule": {"id": "100", "level": 7},
            },
            {
                "id": "a-1",
                "timestamp": "invalid",
                "agent": {"id": "001", "name": "PC-01"},
                "rule": {"id": "101", "level": "bad"},
            },
            {
                "id": "a-3",
                "timestamp": "2026-10-02T00:00:00Z",
                "agent": {},
                "rule": {"id": "102", "level": "8"},
            },
        ]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "alerts.json"
            path.write_text(json.dumps(records), encoding="utf-8")
            report = DataProfilingService.profile(path)

        self.assertEqual(3, report["input"]["total_rows"])
        self.assertEqual(1, report["input"]["unique_agents"])
        self.assertEqual(1, report["quality"]["duplicate_id_rows"])
        self.assertEqual(1, report["quality"]["invalid_timestamp_rows"])
        self.assertEqual(1, report["quality"]["invalid_rule_level_rows"])
        self.assertEqual(1, report["quality"]["required_missing"]["agent.id"])
        self.assertFalse(report["audit"]["cleaning_applied"])
        self.assertEqual(0, report["audit"]["rows_removed"])


if __name__ == "__main__":
    unittest.main()
