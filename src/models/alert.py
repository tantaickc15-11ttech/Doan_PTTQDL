"""Lớp biểu diễn một cảnh báo an ninh."""

import hashlib
import json


class Alert:
    """Lưu các trường cần thiết được chuẩn hóa từ cảnh báo Wazuh."""

    def __init__(
        self,
        alert_id,
        timestamp,
        agent_id,
        agent_name,
        agent_ip,
        rule_id,
        rule_level,
        description,
        groups=None,
        location="",
        raw_data=None,
    ):
        self.alert_id = str(alert_id)
        self.timestamp = str(timestamp)
        self.agent_id = str(agent_id)
        self.agent_name = str(agent_name)
        self.agent_ip = str(agent_ip)
        self.rule_id = str(rule_id)
        self.rule_level = int(rule_level)
        self.description = str(description)
        self.groups = list(groups or [])
        self.location = str(location)
        self.raw_data = raw_data or {}

    @classmethod
    def from_wazuh_dict(cls, data):
        """Tạo Alert từ dictionary Wazuh hoặc dictionary đã chuẩn hóa."""
        if not isinstance(data, dict):
            raise ValueError("Mỗi cảnh báo phải là một dictionary.")

        agent = data.get("agent") or {}
        rule = data.get("rule") or {}

        timestamp = data.get("timestamp", "")
        agent_id = agent.get("id", data.get("agent_id", "unknown"))
        agent_name = agent.get("name", data.get("agent_name", "Không xác định"))
        agent_ip = agent.get("ip", data.get("agent_ip", ""))
        rule_id = rule.get("id", data.get("rule_id", "unknown"))
        rule_level = rule.get("level", data.get("rule_level", 0))
        description = rule.get(
            "description", data.get("description", "Không có mô tả")
        )
        groups = rule.get("groups", data.get("groups", []))
        location = data.get("location", "")

        if not timestamp:
            raise ValueError("Cảnh báo thiếu trường timestamp.")

        try:
            rule_level = int(rule_level)
        except (TypeError, ValueError) as error:
            raise ValueError("rule_level phải là số nguyên.") from error

        if isinstance(groups, str):
            groups = [groups]

        alert_id = data.get("id") or data.get("alert_id")
        if not alert_id:
            unique_text = "|".join(
                [str(timestamp), str(agent_id), str(rule_id), str(description)]
            )
            alert_id = hashlib.sha256(unique_text.encode("utf-8")).hexdigest()[:24]

        return cls(
            alert_id=alert_id,
            timestamp=timestamp,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_ip=agent_ip,
            rule_id=rule_id,
            rule_level=rule_level,
            description=description,
            groups=groups,
            location=location,
            raw_data=data,
        )

    def to_database_tuple(self):
        """Chuyển đối tượng thành tuple dùng cho câu lệnh INSERT SQLite."""
        return (
            self.alert_id,
            self.timestamp,
            self.agent_id,
            self.agent_name,
            self.agent_ip,
            self.rule_id,
            self.rule_level,
            self.description,
            json.dumps(self.groups, ensure_ascii=False),
            self.location,
            json.dumps(self.raw_data, ensure_ascii=False),
        )

    @classmethod
    def from_database_row(cls, row):
        """Tạo Alert từ một dòng kết quả SQLite."""
        try:
            groups = json.loads(row[8] or "[]")
        except json.JSONDecodeError:
            groups = []

        try:
            raw_data = json.loads(row[10] or "{}")
        except json.JSONDecodeError:
            raw_data = {}

        return cls(
            alert_id=row[0],
            timestamp=row[1],
            agent_id=row[2],
            agent_name=row[3],
            agent_ip=row[4],
            rule_id=row[5],
            rule_level=row[6],
            description=row[7],
            groups=groups,
            location=row[9],
            raw_data=raw_data,
        )
