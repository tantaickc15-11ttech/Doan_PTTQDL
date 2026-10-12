"""Kiểm thử HTTP receiver nhận cảnh báo từ Wazuh."""

import json
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from integration.alerts_process import WazuhReceiver


class WazuhReceiverTests(unittest.TestCase):
    def setUp(self):
        self.receiver = WazuhReceiver(
            {
                "enabled": True,
                "host": "127.0.0.1",
                "port": 0,
                "api_key": "test-key",
                "max_body_bytes": 100000,
            }
        )
        self.receiver.start()
        self.url = f"http://127.0.0.1:{self.receiver.port}/alerts"

    def tearDown(self):
        self.receiver.stop()

    def test_accept_valid_alert(self):
        alert = {
            "id": "receiver-001",
            "timestamp": "2026-09-16T10:00:00+07:00",
            "rule": {"id": "100", "level": 10, "description": "Test"},
        }
        request = Request(
            self.url,
            data=json.dumps(alert).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-API-Key": "test-key"},
            method="POST",
        )
        with urlopen(request, timeout=2) as response:
            self.assertEqual(202, response.status)

        time.sleep(0.05)
        self.assertEqual([alert], self.receiver.get_pending())

    def test_reject_invalid_api_key(self):
        request = Request(
            self.url,
            data=b"{}",
            headers={"Content-Type": "application/json", "X-API-Key": "wrong"},
            method="POST",
        )
        try:
            urlopen(request, timeout=2)
            self.fail("Receiver phải từ chối API key sai.")
        except HTTPError as error:
            self.assertEqual(401, error.code)
            error.close()


if __name__ == "__main__":
    unittest.main()
