"""Kiểm thử các chức năng xử lý dữ liệu không phụ thuộc GUI."""

import tempfile
import unittest
from pathlib import Path

from src.models.alert import Alert
from src.services.alert_reader import AlertReader
from src.services.analysis_service import AnalysisService
from src.services.database_service import DatabaseService


PROJECT_DIR = Path(__file__).resolve().parents[1]


class AlertReaderTests(unittest.TestCase):
    def test_read_sample_file(self):
        alerts, errors = AlertReader.read_file(
            PROJECT_DIR / "data" / "sample_alerts.json"
        )
        self.assertEqual(12, len(alerts))
        self.assertEqual([], errors)
        self.assertEqual("WEB-SERVER", alerts[0].agent_name)

    def test_missing_timestamp_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            file_path = Path(directory) / "invalid.json"
            file_path.write_text('[{"rule": {"level": 5}}]', encoding="utf-8")
            alerts, errors = AlertReader.read_file(file_path)
        self.assertEqual([], alerts)
        self.assertEqual(1, len(errors))


class AnalysisServiceTests(unittest.TestCase):
    def setUp(self):
        self.alerts, _errors = AlertReader.read_file(
            PROJECT_DIR / "data" / "sample_alerts.json"
        )

    def test_overview(self):
        result = AnalysisService.overview(self.alerts)
        self.assertEqual(12, result["total"])
        self.assertEqual(6, result["high"])
        self.assertEqual(4, result["agents"])

    def test_severity_total_matches_alert_total(self):
        result = AnalysisService.count_by_severity(self.alerts)
        self.assertEqual(len(self.alerts), sum(result.values()))
        self.assertEqual(2, result["Nghiêm trọng"])

    def test_top_agent(self):
        result = AnalysisService.top_agents(self.alerts)
        self.assertEqual(5, result["WEB-SERVER"])


class DatabaseServiceTests(unittest.TestCase):
    def test_save_filter_and_prevent_duplicate(self):
        alert = Alert.from_wazuh_dict(
            {
                "id": "test-001",
                "timestamp": "2026-09-01T10:00:00+07:00",
                "agent": {"id": "001", "name": "TEST-PC", "ip": "127.0.0.1"},
                "rule": {"id": "100", "level": 9, "description": "Test alert"},
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            database = DatabaseService(Path(directory) / "test.db")
            database.initialize()
            first_result = database.save_alerts([alert])
            second_result = database.save_alerts([alert])
            filtered = database.get_alerts(severity="Cao", agent="TEST-PC")
            filtered_by_ip = database.get_alerts(keyword="127.0.0.1")

        self.assertEqual((1, 0), first_result)
        self.assertEqual((0, 1), second_result)
        self.assertEqual(1, len(filtered))
        self.assertEqual(1, len(filtered_by_ip))


if __name__ == "__main__":
    unittest.main()
