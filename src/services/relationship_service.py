"""Đo mối liên hệ giữa các biến trên bảng Agent/ngày.

KỸ THUẬT: Pearson cho hai biến số và one-way ANOVA cho Agent phân loại.
VẤN ĐỀ: cần bằng chứng thống kê để chọn biến trước khi xây mô hình.
TÁC DỤNG: trả hệ số và p-value; kết quả chỉ là liên hệ, không chứng minh nhân quả.
"""

import pandas as pd
from scipy.stats import pearsonr


class RelationshipService:
    """Measure association without claiming causality or ML importance."""

    CORRELATION_THRESHOLD = 0.3
    P_VALUE_THRESHOLD = 0.05

    NUMERIC_METRICS = [
        "total_events",
        "high_level_alerts",
        "unique_rules",
        "unique_event_ids",
        "unique_source_ips",
        "unique_users",
        "avg_rule_level",
        "max_rule_level",
    ]

    @classmethod
    def correlation_matrix(cls, summary, method="pearson"):
        """Tạo ma trận hệ số tương quan giữa các cặp biến số có sẵn."""
        available = [
            name
            for name in cls.NUMERIC_METRICS
            if name in summary.columns and pd.api.types.is_numeric_dtype(summary[name])
        ]
        if not available or summary.empty:
            return pd.DataFrame()
        return summary[available].corr(method=method)

    @classmethod
    def correlation_with(cls, summary, target="total_events"):
        """Tính Pearson r và p-value của từng biến so với biến mục tiêu."""
        matrix = cls.correlation_matrix(summary)
        columns = [
            "variable",
            "correlation",
            "absolute_correlation",
            "p_value",
            "selected",
            "conclusion",
        ]
        if target not in matrix.columns:
            return pd.DataFrame(columns=columns)

        rows = []
        for variable in matrix.columns:
            if variable == target:
                continue
            pairs = summary[[target, variable]].apply(
                pd.to_numeric, errors="coerce"
            ).dropna()
            if (
                len(pairs) < 2
                or pairs[target].nunique() < 2
                or pairs[variable].nunique() < 2
            ):
                rows.append(
                    {
                        "variable": variable,
                        "correlation": float("nan"),
                        "absolute_correlation": float("nan"),
                        "p_value": float("nan"),
                        "selected": False,
                        "conclusion": "Không đủ dữ liệu hoặc biến không thay đổi",
                    }
                )
                continue
            # r đo chiều/cường độ tuyến tính; p-value đo bằng chứng r khác 0.
            coefficient, p_value = pearsonr(pairs[target], pairs[variable])
            selected = (
                abs(float(coefficient)) > cls.CORRELATION_THRESHOLD
                and float(p_value) < cls.P_VALUE_THRESHOLD
            )
            conclusion = (
                f"{cls.classify_correlation(coefficient)} | "
                f"{cls.classify_p_value(p_value)}"
            )
            rows.append(
                {
                    "variable": variable,
                    "correlation": float(coefficient),
                    "absolute_correlation": abs(float(coefficient)),
                    "p_value": float(p_value),
                    "selected": selected,
                    "conclusion": conclusion,
                }
            )
        result = pd.DataFrame(rows, columns=columns)
        return result.sort_values("absolute_correlation", ascending=False)[columns]

    @staticmethod
    def classify_correlation(value):
        """Classify Pearson r according to the thresholds used in the course."""
        absolute = abs(float(value))
        if absolute >= 0.8:
            strength = "Mạnh"
        elif absolute >= 0.5:
            strength = "Vừa"
        elif absolute >= 0.3:
            strength = "Yếu"
        else:
            return "Không tương quan đáng kể"

        direction = "Đồng thuận" if value > 0 else "Không đồng thuận (nghịch chiều)"
        return f"{strength} - {direction}"

    @staticmethod
    def classify_p_value(p_value):
        """Classify statistical evidence using the thresholds from the course."""
        p_value = float(p_value)
        if p_value < 0.001:
            return "p<0,001: bằng chứng rất mạnh"
        if p_value < 0.05:
            return "p<0,05: bằng chứng vừa"
        if p_value < 0.1:
            return "p<0,1: bằng chứng yếu"
        return "p≥0,1: chưa có bằng chứng"

    @staticmethod
    def anova_by_agent(summary, value_column="total_events"):
        """Compare daily metric means across agents when SciPy is available."""
        try:
            from scipy.stats import f_oneway
        except ImportError:
            return {
                "available": False,
                "reason": "Chưa cài thư viện scipy.",
                "groups": 0,
                "f_statistic": None,
                "p_value": None,
                "conclusion": "Chưa thực hiện",
            }

        groups = []
        for _agent, group in summary.groupby("agent_name"):
            values = pd.to_numeric(group[value_column], errors="coerce").dropna()
            if len(values) >= 2:
                groups.append(values.to_numpy())

        if len(groups) < 2:
            return {
                "available": False,
                "reason": "Cần ít nhất 2 Agent, mỗi Agent có từ 2 ngày dữ liệu.",
                "groups": len(groups),
                "f_statistic": None,
                "p_value": None,
                "conclusion": "Không đủ dữ liệu",
            }

        # ANOVA kiểm tra ít nhất một trung bình Agent khác các nhóm còn lại.
        statistic, p_value = f_oneway(*groups)
        if p_value < 0.05:
            conclusion = (
                "Có sự khác biệt đáng kể giữa các Agent; "
                "chọn biến agent_name"
            )
        else:
            conclusion = (
                "Không có sự khác biệt đáng kể giữa các Agent; "
                "không chọn biến agent_name"
            )
        return {
            "available": True,
            "reason": "",
            "groups": len(groups),
            "f_statistic": float(statistic),
            "p_value": float(p_value),
            "conclusion": conclusion,
        }
