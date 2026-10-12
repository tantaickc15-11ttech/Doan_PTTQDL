"""Kiểm thử bước flatten, lọc và tổng hợp dữ liệu Wazuh."""

import unittest

from src.services.data_preprocessing_service import DataPreprocessingService


class DataPreprocessingServiceTests(unittest.TestCase):
    def setUp(self):
        self.endpoint_alert = {
            "timestamp": "2026-09-19T08:50:58.298+0000",
            "agent": {"id": "005", "name": "ENDPOINT-01", "ip": "10.0.0.5"},
            "rule": {"id": "60122", "level": 10, "description": "Login failed"},
            "decoder": {"name": "windows_eventchannel"},
            "location": "EventChannel",
            "data": {
                "win": {
                    "system": {"eventID": "4625", "severityValue": "3"},
                    "eventdata": {
                        "targetUserName": "demo-user",
                        "ipAddress": "192.168.1.50",
                        "status": "0xc000006d",
                    },
                }
            },
        }

    def test_build_event_dataframe_filters_manager_and_invalid_rows(self):
        manager_alert = {
            "timestamp": "2026-09-19T08:00:00Z",
            "agent": {"id": "000", "name": "wazuh-manager"},
            "rule": {"id": "1", "level": 3},
        }
        missing_agent = {
            "timestamp": "2026-09-19T08:00:00Z",
            "rule": {"id": "2", "level": 4},
        }
        invalid_timestamp = {
            "timestamp": "invalid",
            "agent": {"id": "006", "name": "ENDPOINT-02"},
            "rule": {"id": "3", "level": 5},
        }

        frame = DataPreprocessingService.build_event_dataframe(
            [self.endpoint_alert, manager_alert, missing_agent, invalid_timestamp]
        )

        self.assertEqual(1, len(frame))
        self.assertEqual("005", frame.iloc[0]["agent_id"])
        self.assertEqual("4625", frame.iloc[0]["event_id"])
        self.assertEqual(8, frame.iloc[0]["hour"])

    def test_aggregate_by_agent_creates_expected_metrics(self):
        second_alert = dict(self.endpoint_alert)
        second_alert["timestamp"] = "2026-09-19T09:10:00Z"
        second_alert["rule"] = {
            "id": "60123",
            "level": 12,
            "description": "Another event",
        }

        frame = DataPreprocessingService.build_event_dataframe(
            [self.endpoint_alert, second_alert]
        )
        result = DataPreprocessingService.aggregate_by_agent(frame)

        self.assertEqual(1, len(result))
        self.assertEqual(2, result.iloc[0]["total_events"])
        self.assertEqual(11, result.iloc[0]["avg_rule_level"])
        self.assertEqual(12, result.iloc[0]["max_rule_level"])


if __name__ == "__main__":
    unittest.main()

