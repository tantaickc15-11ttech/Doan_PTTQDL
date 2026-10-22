"""Làm phẳng và chuẩn hóa raw alert Wazuh thành dataset phân tích.

KỸ THUẬT: trích xuất JSON lồng nhau, ép kiểu và groupby Agent/thời gian.
VẤN ĐỀ: raw alert có cấu trúc/kiểu không đồng nhất và nhiều alert mỗi ngày.
TÁC DỤNG: tạo bảng phẳng nhất quán dùng cho EDA và mô hình.
"""

import pandas as pd


class DataPreprocessingService:
    """Tạo event dataset sạch nhưng vẫn giữ nguyên raw data trong SQLite."""

    EVENT_COLUMNS = [
        "timestamp",
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

    @staticmethod
    def _nested_value(data, path):
        """Lấy an toàn giá trị từ đường dẫn JSON dạng `a.b.c`."""
        value = data
        for key in path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(key)
        return value

    @classmethod
    def flatten_alert(cls, raw_alert):
        """Lấy trường cần thiết từ JSON lồng nhau về một dòng phẳng chuẩn."""
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
            "rule_firedtimes": rule.get("firedtimes"),
            "rule_description": rule.get("description"),
            "event_id": cls._nested_value(
                raw_alert, "data.win.system.eventID"
            ),
            "dst_user": cls._nested_value(raw_alert, "data.dstuser"),
            "src_ip": cls._nested_value(raw_alert, "data.srcip"),
            "target_user_name": cls._nested_value(
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
        """Tạo DataFrame, lọc Manager và chuẩn hóa timestamp/kiểu dữ liệu.

        agent.id=000 là Wazuh Manager chứ không phải endpoint cần phân tích;
        timestamp lỗi bị loại vì không thể xếp alert vào đúng ngày.
        """
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
        frame["rule_firedtimes"] = pd.to_numeric(
            frame["rule_firedtimes"], errors="coerce"
        ).astype("Int64")
        identifier_columns = ["rule_id", "event_id"]
        for column in identifier_columns:
            frame[column] = frame[column].astype("string")

        for column in cls.EVENT_COLUMNS:
            if column not in frame:
                frame[column] = pd.NA

        return frame[cls.EVENT_COLUMNS].reset_index(drop=True)

    @staticmethod
    def aggregate_by_agent(frame, frequency="D"):
        """Groupby để gom nhiều alert thành một mẫu Agent/ngày cho mô hình."""
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
                unique_users=("target_user_name", "nunique"),
                unique_source_ips=("src_ip", "nunique"),
                unique_event_ids=("event_id", "nunique"),
            )
            .reset_index()
        )
        return result
