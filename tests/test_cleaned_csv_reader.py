"""Kiểm thử đọc CSV sạch theo batch."""

import csv
import tempfile
import unittest
from pathlib import Path

from src.services.cleaned_csv_reader import CleanedCsvReader


class CleanedCsvReaderTests(unittest.TestCase):
    def test_read_twenty_rows_and_load_next_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.csv"
            self._write_csv(path, total_rows=45)
            reader = CleanedCsvReader(path, batch_size=20)

            first = reader.read_next_batch()
            second = reader.read_next_batch()
            third = reader.read_next_batch()
            empty = reader.read_next_batch()
            reader.close()

        self.assertEqual(20, len(first))
        self.assertEqual("2026-10-01T00:00:00+00:00", first[0]["timestamp_utc"])
        self.assertEqual(20, len(second))
        self.assertEqual(5, len(third))
        self.assertEqual([], empty)

    def test_reset_returns_to_first_row(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clean.csv"
            self._write_csv(path, total_rows=3)
            reader = CleanedCsvReader(path, batch_size=2)
            reader.read_next_batch()
            reader.reset()
            restarted = reader.read_next_batch()
            reader.close()

        self.assertEqual("2026-10-01T00:00:00+00:00", restarted[0]["timestamp_utc"])

    @staticmethod
    def _write_csv(path, total_rows):
        columns = [
            "timestamp_utc",
            "agent_name",
            "rule_id",
            "rule_level",
            "rule_description",
        ]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for index in range(total_rows):
                writer.writerow(
                    {
                        "timestamp_utc": "2026-10-01T00:00:00+00:00",
                        "agent_name": "PC-01",
                        "rule_id": "100",
                        "rule_level": "7",
                        "rule_description": "Test",
                    }
                )


if __name__ == "__main__":
    unittest.main()
