"""Các thao tác lưu và truy vấn cảnh báo bằng SQLite."""

import sqlite3
from contextlib import closing
from pathlib import Path

from src.models.alert import Alert


class DatabaseService:
    """Quản lý cơ sở dữ liệu SQLite của ứng dụng."""

    def __init__(self, database_path):
        self.database_path = Path(database_path)

    def _connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.database_path)

    def initialize(self):
        query = """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                agent_id TEXT,
                agent_name TEXT,
                agent_ip TEXT,
                rule_id TEXT,
                rule_level INTEGER NOT NULL,
                description TEXT,
                groups_json TEXT,
                location TEXT,
                raw_json TEXT
            )
        """
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(query)

    def save_alerts(self, alerts):
        query = """
            INSERT OR IGNORE INTO alerts (
                alert_id, timestamp, agent_id, agent_name, agent_ip,
                rule_id, rule_level, description, groups_json, location,
                raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        inserted = 0
        duplicated = 0

        with closing(self._connect()) as connection:
            with connection:
                for alert in alerts:
                    cursor = connection.execute(query, alert.to_database_tuple())
                    if cursor.rowcount == 1:
                        inserted += 1
                    else:
                        duplicated += 1

        return inserted, duplicated

    def get_alerts(self, keyword="", severity="Tất cả", agent="Tất cả"):
        query = "SELECT * FROM alerts WHERE 1 = 1"
        parameters = []

        keyword = keyword.strip()
        if keyword:
            query += (
                " AND (description LIKE ? OR rule_id LIKE ? "
                "OR agent_name LIKE ? OR agent_ip LIKE ?)"
            )
            search_value = f"%{keyword}%"
            parameters.extend(
                [search_value, search_value, search_value, search_value]
            )

        if severity != "Tất cả":
            ranges = {
                "Thấp": (0, 4),
                "Trung bình": (5, 7),
                "Cao": (8, 11),
                "Nghiêm trọng": (12, 15),
            }
            minimum, maximum = ranges[severity]
            query += " AND rule_level BETWEEN ? AND ?"
            parameters.extend([minimum, maximum])

        if agent != "Tất cả":
            query += " AND agent_name = ?"
            parameters.append(agent)

        query += " ORDER BY timestamp DESC"
        with closing(self._connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [Alert.from_database_row(row) for row in rows]

    def get_agent_names(self):
        query = """
            SELECT DISTINCT agent_name FROM alerts
            WHERE agent_name IS NOT NULL AND agent_name != ''
            ORDER BY agent_name
        """
        with closing(self._connect()) as connection:
            rows = connection.execute(query).fetchall()
        return [row[0] for row in rows]
