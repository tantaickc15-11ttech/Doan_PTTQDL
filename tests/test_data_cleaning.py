"""Kiểm thử validation, cleaning và đẳng thức kiểm toán."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.services.data_cleaning_service import DataCleaningService


class DataCleaningServiceTests(unittest.TestCase):
    def test_keep_first_duplicate_and_preserve_optional_missing(self):
        records = [
            self._record("same-id", "First description"),
            self._record("same-id", "Second description"),
        ]

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.json"
            output = Path(directory) / "clean.csv"
            source.write_text(json.dumps(records), encoding="utf-8")

            report = DataCleaningService.clean_to_csv(source, output)
            with output.open("r", encoding="utf-8", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))

        self.assertEqual(1, len(rows))
        self.assertEqual("First description", rows[0]["rule_description"])
        self.assertEqual("", rows[0]["event_id"])
        self.assertEqual(1, report["actions"]["removed_by_reason"]["duplicate_alert_id"])
        self.assertTrue(report["audit"]["equation_valid"])

    def test_removed_reasons_are_mutually_exclusive(self):
        records = [
            self._record("valid", "Valid"),
            {
                "id": "missing-agent",
                "timestamp": "invalid",
                "agent": {},
                "rule": {"id": "2", "level": "bad"},
            },
            {
                "id": "manager",
                "timestamp": "2026-10-01T00:00:00Z",
                "agent": {"id": "000"},
                "rule": {"id": "3", "level": 7},
            },
        ]

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.json"
            output = Path(directory) / "clean.csv"
            source.write_text(json.dumps(records), encoding="utf-8")
            report = DataCleaningService.clean_to_csv(source, output)

        reasons = report["actions"]["removed_by_reason"]
        self.assertEqual(1, reasons["missing_agent_id"])
        self.assertEqual(1, reasons["manager_agent_000"])
        self.assertEqual(2, report["actions"]["removed_unique_rows"])
        self.assertEqual(3, report["before"]["input_rows"])
        self.assertEqual(1, report["after"]["output_rows"])
        self.assertTrue(report["audit"]["equation_valid"])

    @staticmethod
    def _record(alert_id, description):
        return {
            "id": alert_id,
            "timestamp": "2026-10-01T07:30:00+0700",
            "agent": {"id": "001", "name": "PC-01", "ip": "10.0.0.1"},
            "rule": {
                "id": "100",
                "level": 7,
                "description": description,
                "groups": ["security"],
                "mitre": {"id": ["T1001"]},
            },
            "manager": {"name": "manager"},
            "decoder": {"name": "json"},
        }


if __name__ == "__main__":
    unittest.main()
