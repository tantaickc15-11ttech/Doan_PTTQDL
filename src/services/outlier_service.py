"""Phân tích ngoại lệ và hình dạng phân phối trên dữ liệu Agent/ngày.

KỸ THUẬT: 1.5×IQR, skewness, excess kurtosis và KDE.
VẤN ĐỀ: cần phân biệt điểm bất thường, độ lệch và độ nhọn của phân phối.
TÁC DỤNG: cung cấp ngưỡng số học và đường mật độ để giải thích trực quan.
"""

import pandas as pd
from scipy.stats import gaussian_kde


class OutlierService:
    """Apply the documented 1.5 x IQR rule to meaningful numeric metrics."""

    ALL_LEVEL_GROUPS = "Tất cả"
    METRICS = {
        "Event Level 0-7": "level_0_7_events",
        "Event Level 7-10": "level_8_10_events",
        "Event Level lớn hơn 10": "level_above_10_events",
    }

    @classmethod
    def analyze(cls, summary, selection):
        """Chọn đúng cột Event Level rồi thực hiện cùng một phép phân tích."""
        if selection not in cls.METRICS:
            raise ValueError(f"Nhóm Event Level không hợp lệ: {selection}")

        metric = cls.METRICS[selection]
        return cls._analyze_metric(summary, metric, selection)

    @classmethod
    def analyze_total(cls, summary):
        """Analyze the distribution of all Event Levels combined."""
        return cls._analyze_metric(summary, "total_events", "Tất cả Event")

    @classmethod
    def analyze_total_events_by_agent(cls, summary):
        """Analyze daily total Event counts independently for every Agent."""
        if summary.empty or "agent_name" not in summary.columns:
            return []

        results = []
        for agent, agent_summary in summary.groupby("agent_name", sort=True):
            result = cls._analyze_metric(
                agent_summary, "total_events", str(agent)
            )
            result["agent_name"] = str(agent)
            results.append(result)
        return results

    @classmethod
    def _analyze_metric(cls, summary, metric, label):
        """Calculate IQR, skewness, kurtosis and KDE for one numeric metric."""

        values = pd.to_numeric(summary.get(metric), errors="coerce").dropna()
        if values.empty:
            return {
                "metric": metric,
                "label": label,
                "q1": 0.0,
                "q2": 0.0,
                "q3": 0.0,
                "iqr": 0.0,
                "lower_bound": 0.0,
                "upper_bound": 0.0,
                "outlier_count": 0,
                "outliers": pd.DataFrame(),
                "values": values,
                "skewness": 0.0,
                "skew_conclusion": "Đối xứng",
                "kurtosis": 0.0,
                "kurtosis_conclusion": "Độ nhọn bằng phân phối chuẩn",
                "density_x": [],
                "density_y": [],
            }

        # IQR: điểm ngoài [Q1 - 1.5*IQR, Q3 + 1.5*IQR] là ngoại lệ thống kê.
        q1 = float(values.quantile(0.25))
        q2 = float(values.quantile(0.50))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        mask = ((summary[metric] < lower) | (summary[metric] > upper)).fillna(False)
        outliers = summary.loc[mask, ["agent_name", "event_date", metric]].copy()
        outliers = outliers.rename(columns={metric: "value"})
        outliers["conclusion"] = "Outlier thống kê"
        outliers = outliers.sort_values("value", ascending=False)

        # skew=0 gần đối xứng, >0 lệch phải, <0 lệch trái.
        # kurt() ở đây là excess kurtosis: 0 tương đương độ nhọn phân phối chuẩn.
        skewness = float(values.skew()) if len(values) >= 3 else 0.0
        if pd.isna(skewness):
            skewness = 0.0
        if skewness > 0:
            skew_conclusion = "Lệch phải - về phía giá trị cao"
        elif skewness < 0:
            skew_conclusion = "Lệch trái - về phía giá trị thấp"
        else:
            skew_conclusion = "Đối xứng"

        # pandas.Series.kurt() returns Fisher's excess kurtosis: normal = 0.
        kurtosis = float(values.kurt()) if len(values) >= 4 else 0.0
        if pd.isna(kurtosis):
            kurtosis = 0.0
        if kurtosis > 0:
            kurtosis_conclusion = "Độ nhọn cao hơn phân phối chuẩn"
        elif kurtosis < 0:
            kurtosis_conclusion = "Độ nhọn thấp hơn phân phối chuẩn"
        else:
            kurtosis_conclusion = "Độ nhọn bằng phân phối chuẩn"

        density_x = []
        density_y = []
        if len(values) >= 2 and values.nunique() >= 2:
            minimum = float(values.min())
            maximum = float(values.max())
            padding = (maximum - minimum) * 0.15
            density_lower = max(0.0, minimum - padding)
            density_upper = maximum + padding
            point_count = 200
            step = (density_upper - density_lower) / (point_count - 1)
            density_x = [
                density_lower + index * step for index in range(point_count)
            ]
            density_y = gaussian_kde(values.to_numpy())(density_x)

        return {
            "metric": metric,
            "label": label,
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "iqr": iqr,
            "lower_bound": lower,
            "upper_bound": upper,
            "outlier_count": int(len(outliers)),
            "outliers": outliers,
            "values": values,
            "skewness": skewness,
            "skew_conclusion": skew_conclusion,
            "kurtosis": kurtosis,
            "kurtosis_conclusion": kurtosis_conclusion,
            "density_x": density_x,
            "density_y": density_y,
        }

    @classmethod
    def analyze_selection(cls, summary, selection):
        """Analyze the metric selected for comparison across Agents."""
        if selection == cls.ALL_LEVEL_GROUPS:
            return [cls.analyze_total(summary)]
        return [cls.analyze(summary, selection)]
