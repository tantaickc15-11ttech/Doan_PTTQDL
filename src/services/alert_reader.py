"""Đọc và kiểm tra dữ liệu cảnh báo từ file JSON."""

import json
from pathlib import Path

from src.models.alert import Alert


class AlertReader:
    """Hỗ trợ JSON array, một JSON object và định dạng JSON Lines."""

    @staticmethod
    #Hỗ trợ đọc file Json đầu vào
    def read_file(file_path):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file: {path}")

        text = path.read_text(encoding="utf-8-sig").strip()
        if not text:
            raise ValueError("File dữ liệu đang rỗng.")

        records = AlertReader._parse_records(text)
        alerts = []
        errors = []

        for index, record in enumerate(records, start=1):
            try:
                alerts.append(Alert.from_wazuh_dict(record))
            except (TypeError, ValueError) as error:
                errors.append(f"Bản ghi {index}: {error}")

        return alerts, errors

    @staticmethod
    #kiểm tra cú pháp JSON và chuyển dữ liệu từ chuỗi text thành Dir hoặc 1 list dir
    def _parse_records(text):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            records = []
            for line_number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"JSON không hợp lệ tại dòng {line_number}."
                    ) from error
            return records

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            affected_items = data.get("data", {}).get("affected_items")
            if isinstance(affected_items, list):
                return affected_items
            return [data]

        raise ValueError("Dữ liệu JSON phải là object hoặc danh sách object.")

