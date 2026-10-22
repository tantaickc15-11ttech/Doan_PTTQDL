"""Quy tắc điểm rủi ro dùng cho phần xử lý dữ liệu tham khảo.

KỸ THUẬT: ánh xạ rule.level theo ngưỡng nghiệp vụ. Đây là rule-based scoring,
không phải học máy và không tham gia dự đoán ``total_events`` hiện tại.
"""

import pandas as pd


class RiskScoringService:
    """Convert Wazuh rule levels into additive per-alert risk points."""

    MEDIUM_LEVEL = 8
    HIGH_LEVEL = 11
    CRITICAL_LEVEL = 13

    LOW_SCORE = 1
    MEDIUM_SCORE = 4
    HIGH_SCORE = 16
    CRITICAL_SCORE = 64

    @staticmethod
    def event_score(rule_level):
        """Return the risk contribution of one alert from its Wazuh Level."""
        level = int(rule_level)
        if level < RiskScoringService.MEDIUM_LEVEL:
            return RiskScoringService.LOW_SCORE
        if level < RiskScoringService.HIGH_LEVEL:
            return RiskScoringService.MEDIUM_SCORE
        if level < RiskScoringService.CRITICAL_LEVEL:
            return RiskScoringService.HIGH_SCORE
        return RiskScoringService.CRITICAL_SCORE

    @classmethod
    def event_scores(cls, rule_levels):
        """Vectorized version of :meth:`event_score` for a pandas Series."""
        levels = pd.to_numeric(rule_levels, errors="coerce")
        scores = pd.Series(pd.NA, index=levels.index, dtype="Int64")
        scores.loc[levels < cls.MEDIUM_LEVEL] = cls.LOW_SCORE
        scores.loc[
            levels.between(cls.MEDIUM_LEVEL, cls.HIGH_LEVEL - 1)
        ] = cls.MEDIUM_SCORE
        scores.loc[
            levels.between(cls.HIGH_LEVEL, cls.CRITICAL_LEVEL - 1)
        ] = cls.HIGH_SCORE
        scores.loc[levels >= cls.CRITICAL_LEVEL] = cls.CRITICAL_SCORE
        return scores

    @classmethod
    def classify_level(cls, rule_level):
        """Map one Wazuh Level to Low, Medium, High or Critical."""
        level = int(rule_level)
        if level < cls.MEDIUM_LEVEL:
            return "Low"
        if level < cls.HIGH_LEVEL:
            return "Medium"
        if level < cls.CRITICAL_LEVEL:
            return "High"
        return "Critical"

    @classmethod
    def classify_score(cls, risk_score):
        """Classify one alert's discrete risk contribution."""
        score = float(risk_score)
        if score >= cls.CRITICAL_SCORE:
            return "Critical"
        if score >= cls.HIGH_SCORE:
            return "High"
        if score >= cls.MEDIUM_SCORE:
            return "Medium"
        return "Low"
