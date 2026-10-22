"""Thống kê baseline của raw Wazuh dataset trước khi làm sạch.

KỸ THUẬT: profiling một lượt (one-pass) kết hợp Counter và set.
VẤN ĐỀ: phải biết thiếu trường, sai kiểu và trùng ID trước khi quyết định làm sạch.
TÁC DỤNG: tạo bằng chứng trước xử lý mà không chỉnh sửa raw dataset.
"""

import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.services.json_stream_reader import JsonStreamReader


class DataProfilingService:
    """Kiểm kê cấu trúc, missing, sai kiểu và duplicate ID."""

    FIELD_PATHS = [
        "id",
        "timestamp",
        "agent.id",
        "agent.name",
        "agent.ip",
        "rule.id",
        "rule.level",
        "rule.firedtimes",
        "rule.description",
        "rule.groups",
        "rule.mitre",
        "manager.name",
        "decoder.name",
        "location",
        "data.win.system.eventID",
        "data.win.system.severityValue",
        "data.win.eventdata.targetUserName",
        "data.win.eventdata.ipAddress",
        "data.win.eventdata.status",
        "data.dstuser",
        "data.srcip",
        "full_log",
    ]

    REQUIRED_FIELDS = ["id", "timestamp", "agent.id", "rule.id", "rule.level"]

    @classmethod
    def profile(cls, file_path, progress_callback=None):
        """Duyệt đúng một lần và trả báo cáo chất lượng trước cleaning."""
        path = Path(file_path)
        started = time.perf_counter()
        started_at = datetime.now(timezone.utc)

        total_rows = 0
        top_level_fields = set()
        unique_agents = set()
        seen_alert_ids = set()
        duplicated_alert_ids = set()
        duplicate_id_rows = 0
        missing_counts = Counter()
        type_counts = {field: Counter() for field in cls.FIELD_PATHS}
        invalid_timestamp_rows = 0
        invalid_rule_level_rows = 0
        minimum_timestamp = None
        maximum_timestamp = None

        # One-pass profiling: cập nhật mọi bộ đếm ngay khi record được stream tới.
        for record in JsonStreamReader.iter_records(path):
            total_rows += 1
            top_level_fields.update(record.keys())

            values = {
                field: cls._nested_value(record, field) for field in cls.FIELD_PATHS
            }
            for field, value in values.items():
                if cls._is_missing(value):
                    missing_counts[field] += 1
                else:
                    type_counts[field][type(value).__name__] += 1

            alert_id = values["id"]
            if not cls._is_missing(alert_id):
                alert_id = str(alert_id)
                if alert_id in seen_alert_ids:
                    duplicate_id_rows += 1
                    duplicated_alert_ids.add(alert_id)
                else:
                    seen_alert_ids.add(alert_id)

            agent_id = values["agent.id"]
            if not cls._is_missing(agent_id):
                unique_agents.add(str(agent_id))

            parsed_timestamp = cls._parse_timestamp(values["timestamp"])
            if parsed_timestamp is None:
                invalid_timestamp_rows += 1
            else:
                if minimum_timestamp is None or parsed_timestamp < minimum_timestamp:
                    minimum_timestamp = parsed_timestamp
                if maximum_timestamp is None or parsed_timestamp > maximum_timestamp:
                    maximum_timestamp = parsed_timestamp

            if not cls._is_valid_rule_level(values["rule.level"]):
                invalid_rule_level_rows += 1

            if progress_callback and total_rows % 10000 == 0:
                progress_callback(total_rows)

        field_report = {}
        for field in cls.FIELD_PATHS:
            missing = missing_counts[field]
            field_report[field] = {
                "present": total_rows - missing,
                "missing": missing,
                "missing_percent": cls._percentage(missing, total_rows),
                "types": dict(sorted(type_counts[field].items())),
            }

        required_missing = {
            field: missing_counts[field] for field in cls.REQUIRED_FIELDS
        }

        return {
            "metadata": {
                "generated_at_utc": started_at.isoformat(),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "input_file": path.name,
                "file_size_bytes": path.stat().st_size,
                "format": JsonStreamReader.detect_format(path),
                "stage": "profiling_before_cleaning",
            },
            "input": {
                "total_rows": total_rows,
                "unique_agents": len(unique_agents),
                "minimum_timestamp_utc": cls._format_timestamp(minimum_timestamp),
                "maximum_timestamp_utc": cls._format_timestamp(maximum_timestamp),
                "top_level_fields": sorted(top_level_fields),
                "profiled_fields": len(cls.FIELD_PATHS),
            },
            "quality": {
                "unique_alert_ids": len(seen_alert_ids),
                "duplicate_id_rows": duplicate_id_rows,
                "duplicated_id_values": len(duplicated_alert_ids),
                "required_missing": required_missing,
                "invalid_timestamp_rows": invalid_timestamp_rows,
                "invalid_rule_level_rows": invalid_rule_level_rows,
            },
            "fields": field_report,
            "audit": {
                "cleaning_applied": False,
                "rows_removed": 0,
                "note": "Baseline trước cleaning; chưa loại duplicate hoặc missing.",
            },
        }

    @staticmethod
    def save_report(report, output_path):
        """Ghi báo cáo profiling ra JSON UTF-8."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _nested_value(record, dotted_path):
        """Lấy an toàn một trường JSON lồng nhau theo đường dẫn dấu chấm."""
        value = record
        for key in dotted_path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    @staticmethod
    def _is_missing(value):
        """Nhận diện None, NaN và chuỗi rỗng để đếm missing."""
        return value is None or value == ""

    @staticmethod
    def _is_valid_rule_level(value):
        """Kiểm tra rule level có thể biểu diễn bằng số nguyên hay không."""
        if isinstance(value, bool) or value is None:
            return False
        if isinstance(value, int):
            return True
        if isinstance(value, float):
            return math.isfinite(value) and value.is_integer()
        if isinstance(value, str):
            try:
                int(value)
                return True
            except ValueError:
                return False
        return False

    @staticmethod
    def _parse_timestamp(value):
        """Parse timestamp về UTC để xác định phạm vi thời gian dataset."""
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _format_timestamp(value):
        """Đổi datetime thành ISO 8601 hoặc None cho báo cáo JSON."""
        return value.isoformat() if value is not None else None

    @staticmethod
    def _percentage(value, total):
        """Tính phần trăm, tránh chia cho 0 khi dataset rỗng."""
        if total == 0:
            return 0.0
        return round(value * 100 / total, 4)
