"""Các hàm thống kê phục vụ Dashboard và biểu đồ."""

from collections import Counter
from datetime import datetime


class AnalysisService:
    """Phân tích một danh sách đối tượng Alert bằng Python cơ bản."""

    @staticmethod
    def severity_name(level):
        if level <= 4:
            return "Thấp"
        if level <= 7:
            return "Trung bình"
        if level <= 11:
            return "Cao"
        return "Nghiêm trọng"

    @staticmethod
    def overview(alerts):
        high_count = 0
        agents = set()

        for alert in alerts:
            if alert.rule_level >= 8:
                high_count += 1
            agents.add(alert.agent_name)

        return {
            "total": len(alerts),
            "high": high_count,
            "agents": len(agents),
        }

    @staticmethod
    def count_by_severity(alerts):
        result = {"Thấp": 0, "Trung bình": 0, "Cao": 0, "Nghiêm trọng": 0}
        for alert in alerts:
            result[AnalysisService.severity_name(alert.rule_level)] += 1
        return result

    @staticmethod
    def count_by_date(alerts):
        counts = Counter()
        for alert in alerts:
            date_text = AnalysisService._get_date(alert.timestamp)
            if date_text:
                counts[date_text] += 1
        return dict(sorted(counts.items()))

    @staticmethod
    def top_agents(alerts, limit=5):
        counts = Counter(alert.agent_name for alert in alerts)
        return dict(counts.most_common(limit))

    @staticmethod
    def top_rules(alerts, limit=5):
        counts = Counter(alert.rule_id for alert in alerts)
        return dict(counts.most_common(limit))

    @staticmethod
    def _get_date(timestamp):
        value = str(timestamp).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(value).strftime("%Y-%m-%d")
        except ValueError:
            return ""
