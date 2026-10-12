#!/usr/bin/env python3
"""Integration độc lập gửi raw event Wazuh sang ứng dụng đồ án."""

import json
import sys

import requests


def main():
    if len(sys.argv) < 4:
        print(
            "Thiếu tham số: alert_file, api_key hoặc receiver_url.",
            file=sys.stderr,
        )
        return 1

    alert_file = sys.argv[1]
    api_key = sys.argv[2]
    receiver_url = sys.argv[3]

    try:
        with open(alert_file, "r", encoding="utf-8") as file:
            alert_json = json.load(file)

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        response = requests.post(
            receiver_url,
            headers=headers,
            json=alert_json,
            timeout=5,
        )
        response.raise_for_status()
        return 0
    except (OSError, json.JSONDecodeError, requests.RequestException) as error:
        print(f"Không chuyển được event sang project: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

