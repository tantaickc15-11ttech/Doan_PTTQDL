"""Validation, deduplicate và chuẩn hóa raw Wazuh dataset theo streaming.

KỸ THUẬT: kiểm tra schema, chuẩn hóa UTC/kiểu số, khử trùng alert ID và ghi
file tạm rồi thay thế nguyên tử.
VẤN ĐỀ: raw JSON có thể thiếu/sai/trùng; lỗi giữa chừng không được làm hỏng CSV.
TÁC DỤNG: tạo CSV sạch có báo cáo kiểm toán số dòng trước và sau xử lý.
"""

import csv
import json
import math
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.services.json_stream_reader import JsonStreamReader
class DataCleaningService:
    """Tạo CSV sạch, giữ bản ghi đầu tiên khi trùng alert ID."""

    OUTPUT_COLUMNS = [
        "timestamp_utc",
        "agent_name",
        "source_ip",
        "src_ip",
        "dst_user",
        "target_user_name",
        "event_id",
        "rule_id",
        "rule_level",
        "rule_firedtimes",
        "rule_description",
    ]

    REQUIRED_PATHS = ["id", "timestamp", "agent.id", "rule.id", "rule.level"]

    @classmethod
    def clean_to_csv(
        cls,
        input_path,
        output_path,
        progress_callback=None,
    ):
        """Làm sạch raw JSON và ghi CSV theo cách streaming."""
        source_path = Path(input_path)
        destination_path = Path(output_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = destination_path.with_suffix(destination_path.suffix + ".tmp")

        # Ghi vào .tmp trước; chỉ replace file đích sau khi toàn bộ quá trình
        # thành công. Nếu lỗi, file tạm bị xóa và dữ liệu cũ vẫn nguyên vẹn.

        started_at = datetime.now(timezone.utc)
        started = time.perf_counter()
        seen_alert_ids = set()
        removed_by_reason = Counter()
        total_rows = 0
        output_rows = 0
        timestamp_values_standardized = 0
        rule_level_values_converted = 0
        example_before = None
        example_after = None

        try:
            with temporary_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=cls.OUTPUT_COLUMNS)
                writer.writeheader()

                # Streaming: kiểm tra và ghi từng record, không giữ toàn file trong RAM.
                for record in JsonStreamReader.iter_records(source_path):
                    total_rows += 1
                    reason, normalized = cls._validate_and_normalize(record)

                    if reason:
                        removed_by_reason[reason] += 1
                    # Deduplication: alert ID đã gặp bị bỏ, giữ bản hợp lệ đầu tiên.
                    elif normalized["alert_id"] in seen_alert_ids:
                        removed_by_reason["duplicate_alert_id"] += 1
                    else:
                        seen_alert_ids.add(normalized["alert_id"])
                        writer.writerow(
                            {
                                column: normalized[column]
                                for column in cls.OUTPUT_COLUMNS
                            }
                        )
                        output_rows += 1
                        timestamp_values_standardized += 1
                        if not isinstance(cls._nested_value(record, "rule.level"), int):
                            rule_level_values_converted += 1

                        if example_before is None:
                            example_before = cls._safe_raw_example(record)
                            example_after = cls._safe_normalized_example(normalized)

                    if progress_callback and total_rows % 10000 == 0:
                        progress_callback(total_rows)

            temporary_path.replace(destination_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        removed_unique_rows = sum(removed_by_reason.values())
        if total_rows != output_rows + removed_unique_rows:
            raise RuntimeError("Số liệu cleaning không thỏa mãn đẳng thức kiểm toán.")

        return {
            "metadata": {
                "generated_at_utc": started_at.isoformat(),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "input_file": source_path.name,
                "output_file": destination_path.name,
                "duplicate_rule": "keep_first_valid_occurrence",
                "timestamp_standard": "UTC ISO 8601",
            },
            "before": {
                "input_rows": total_rows,
            },
            "actions": {
                "removed_by_reason": dict(sorted(removed_by_reason.items())),
                "removed_unique_rows": removed_unique_rows,
                "timestamp_values_standardized": timestamp_values_standardized,
                "rule_level_values_converted": rule_level_values_converted,
            },
            "after": {
                "output_rows": output_rows,
                "retention_percent": cls._percentage(output_rows, total_rows),
                "output_columns": len(cls.OUTPUT_COLUMNS),
                "unique_alert_ids": len(seen_alert_ids),
            },
            "audit": {
                "equation": "input_rows = output_rows + removed_unique_rows",
                "equation_valid": total_rows == output_rows + removed_unique_rows,
                "raw_file_modified": False,
            },
            "sample_transformation": {
                "before": example_before,
                "after": example_after,
                "sensitive_values_redacted": True,
            },
        }

    @staticmethod
    def save_report(report, output_path):
        """Ghi cleaning report ra JSON UTF-8."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def _validate_and_normalize(cls, record):
        """Trả lý do loại hoặc một record đã chuẩn hóa đúng schema đầu ra."""
        if not isinstance(record, dict):
            return "not_json_object", None

        for field in cls.REQUIRED_PATHS:
            if cls._is_missing(cls._nested_value(record, field)):
                return f"missing_{field.replace('.', '_')}", None

        # Chuẩn hóa mọi timezone về UTC để lọc và nhóm theo ngày không lệch múi giờ.
        timestamp = cls._parse_timestamp(record.get("timestamp"))
        if timestamp is None:
            return "invalid_timestamp", None

        rule_level = cls._parse_rule_level(cls._nested_value(record, "rule.level"))
        if rule_level is None:
            return "invalid_rule_level", None

        agent_id = str(cls._nested_value(record, "agent.id"))
        if agent_id == "000":
            return "manager_agent_000", None

        normalized = {
            "alert_id": str(record["id"]),
            "timestamp_utc": timestamp.isoformat(),
            "agent_name": cls._optional_text(cls._nested_value(record, "agent.name")),
            "rule_id": str(cls._nested_value(record, "rule.id")),
            "rule_level": rule_level,
            "rule_firedtimes": cls._optional_number(
                cls._nested_value(record, "rule.firedtimes")
            ),
            "rule_description": cls._optional_text(
                cls._nested_value(record, "rule.description")
            ),
            "event_id": cls._optional_text(
                cls._nested_value(record, "data.win.system.eventID")
            ),
            "source_ip": cls._optional_text(
                cls._nested_value(record, "data.win.eventdata.ipAddress")
            ),
            "dst_user": cls._optional_text(
                cls._nested_value(record, "data.dstuser")
            ),
            "src_ip": cls._optional_text(cls._nested_value(record, "data.srcip")),
            "target_user_name": cls._optional_text(
                cls._nested_value(record, "data.win.eventdata.targetUserName")
            ),
        }
        return None, normalized

    @staticmethod
    def _nested_value(record, dotted_path):
        """Lấy giá trị JSON lồng nhau; trả None nếu một nhánh không tồn tại."""
        value = record
        for key in dotted_path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    @staticmethod
    def _is_missing(value):
        """Xác định None, NaN hoặc chuỗi rỗng là dữ liệu thiếu."""
        return value is None or value == ""

    @staticmethod
    def _parse_timestamp(value):
        """Chuyển timestamp hợp lệ về datetime UTC; lỗi trả None."""
        if not isinstance(value, str):
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
    def _parse_rule_level(value):
        """Chuyển rule level về số nguyên hợp lệ; lỗi trả None."""
        if isinstance(value, bool) or value is None:
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
            return None
        return parsed

    @staticmethod
    def _optional_text(value):
        """Chuẩn hóa trường chữ tùy chọn mà không tạo nội dung giả."""
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _optional_number(value):
        """Chuẩn hóa trường số tùy chọn, giữ rỗng nếu không có dữ liệu."""
        if value is None or value == "":
            return ""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return ""
        if not math.isfinite(number):
            return ""
        return int(number) if number.is_integer() else number

    @staticmethod
    def _list_to_text(value):
        """Ghép list thành chuỗi CSV; giá trị đơn được chuyển sang text."""
        if value is None:
            return ""
        if isinstance(value, list):
            return "|".join(str(item) for item in value)
        return str(value)

    @classmethod
    def _safe_raw_example(cls, record):
        """Tạo ví dụ raw đã che thông tin nhạy cảm cho cleaning report."""
        return {
            "id": record.get("id"),
            "timestamp": record.get("timestamp"),
            "agent": {
                "id": cls._nested_value(record, "agent.id"),
                "name": "***",
                "ip": "***",
            },
            "rule": {
                "id": cls._nested_value(record, "rule.id"),
                "level": cls._nested_value(record, "rule.level"),
                "groups": cls._nested_value(record, "rule.groups"),
            },
        }

    @staticmethod
    def _safe_normalized_example(record):
        """Tạo ví dụ sau chuẩn hóa đã che thông tin nhạy cảm."""
        safe_record = record.copy()
        for field in (
            "agent_name",
            "source_ip",
            "dst_user",
            "src_ip",
            "target_user_name",
        ):
            if safe_record.get(field):
                safe_record[field] = "***"
        return safe_record

    @staticmethod
    def _percentage(value, total):
        """Tính tỷ lệ phần trăm an toàn khi tổng có thể bằng 0."""
        if total == 0:
            return 0.0
        return round(value * 100 / total, 4)
