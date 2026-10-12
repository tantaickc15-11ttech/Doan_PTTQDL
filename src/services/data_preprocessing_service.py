"""Làm phẳng và chuẩn hóa raw alert Wazuh thành dataset phân tích."""

import pandas as pd


class DataPreprocessingService:
    """Tạo event dataset sạch nhưng vẫn giữ nguyên raw data trong SQLite."""

    EVENT_COLUMNS = [
        "timestamp",
        "date",
        "hour",
        "agent_id",
        "agent_name",
        "agent_ip",
        "rule_id",
        "rule_level",
        "rule_description",
        "event_id",
        "severity_value",
        "target_user",
        "source_ip",
        "status",
        "decoder",
        "location",
    ]

    @staticmethod
    def _nested_value(data, path):
        value = data
        for key in path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    @classmethod
    def flatten_alert(cls, raw_alert):
        """Lấy các field phân tích từ một raw JSON mà không tự điền sai ngữ nghĩa."""
        if not isinstance(raw_alert, dict):
            raise ValueError("Raw alert phải là một dictionary.")

        agent = raw_alert.get("agent") or {}
        rule = raw_alert.get("rule") or {}

        return {
            "timestamp": raw_alert.get("timestamp"),
            "agent_id": agent.get("id"),
            "agent_name": agent.get("name"),
            "agent_ip": agent.get("ip"),
            "rule_id": rule.get("id"),
            "rule_level": rule.get("level"),
            "rule_description": rule.get("description"),
            "event_id": cls._nested_value(
                raw_alert, "data.win.system.eventID"
            ),
            "severity_value": cls._nested_value(
                raw_alert, "data.win.system.severityValue"
            ),
            "target_user": cls._nested_value(
                raw_alert, "data.win.eventdata.targetUserName"
            ),
            "source_ip": cls._nested_value(
                raw_alert, "data.win.eventdata.ipAddress"
            ),
            "status": cls._nested_value(
                raw_alert, "data.win.eventdata.status"
            ),
            "decoder": cls._nested_value(raw_alert, "decoder.name"),
            "location": raw_alert.get("location"),
        }

    @classmethod
    def build_event_dataframe(cls, records):
        """Tạo DataFrame, lọc Manager và chuẩn hóa timestamp/kiểu dữ liệu."""
        flattened = []
        for record in records:
            raw_alert = getattr(record, "raw_data", record)
            flattened.append(cls.flatten_alert(raw_alert))

        frame = pd.DataFrame(flattened)
        if frame.empty:
            return pd.DataFrame(columns=cls.EVENT_COLUMNS)

        # Chỉ giữ log từ endpoint thật, loại Wazuh Manager có agent.id = 000.
        frame["agent_id"] = frame["agent_id"].astype("string")
        frame = frame[frame["agent_id"].notna() & (frame["agent_id"] != "000")]

        # Chuẩn hóa nhiều dạng timezone về UTC; timestamp lỗi không dùng cho EDA.
        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], format="mixed", errors="coerce", utc=True
        )
        frame = frame.dropna(subset=["timestamp"])

        frame["rule_level"] = pd.to_numeric(
            frame["rule_level"], errors="coerce"
        ).astype("Int64")
        frame["severity_value"] = pd.to_numeric(
            frame["severity_value"], errors="coerce"
        ).astype("Int64")

        identifier_columns = ["rule_id", "event_id"]
        for column in identifier_columns:
            frame[column] = frame[column].astype("string")

        frame["date"] = frame["timestamp"].dt.date
        frame["hour"] = frame["timestamp"].dt.hour.astype("Int64")

        for column in cls.EVENT_COLUMNS:
            if column not in frame:
                frame[column] = pd.NA

        return frame[cls.EVENT_COLUMNS].reset_index(drop=True)

    @staticmethod
    def aggregate_by_agent(frame, frequency="D"):
        """Tổng hợp các chỉ số chắc chắn có ý nghĩa theo Agent và thời gian."""
        if frame.empty:
            return pd.DataFrame(
                columns=[
                    "agent_name",
                    "time_bucket",
                    "total_events",
                    "avg_rule_level",
                    "max_rule_level",
                    "unique_users",
                    "unique_source_ips",
                    "unique_event_ids",
                ]
            )

        data = frame.copy()
        data["time_bucket"] = data["timestamp"].dt.floor(frequency)

        result = (
            data.groupby(["agent_name", "time_bucket"], dropna=False)
            .agg(
                total_events=("rule_id", "size"),
                avg_rule_level=("rule_level", "mean"),
                max_rule_level=("rule_level", "max"),
                unique_users=("target_user", "nunique"),
                unique_source_ips=("source_ip", "nunique"),
                unique_event_ids=("event_id", "nunique"),
            )
            .reset_index()
        )
        return result
