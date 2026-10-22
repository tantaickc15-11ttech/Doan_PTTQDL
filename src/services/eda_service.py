"""Nạp, lọc và tổng hợp dataset Wazuh phục vụ EDA.

KỸ THUẬT: ép kiểu, lọc Boolean, thống kê mô tả, pivot và groupby.
VẤN ĐỀ: mọi biểu đồ phải dùng cùng quy tắc lọc và cùng nguồn số liệu.
TÁC DỤNG: tách phép tính khỏi giao diện để kết quả nhất quán, dễ kiểm thử.
"""

from pathlib import Path

import pandas as pd



class EdaService:
    """Keep data-processing rules separate from the Tkinter interface."""

    ALL_AGENTS = "Tất cả"
    ALL_LEVELS = "Tất cả"
    HIGH_LEVEL_MIN = 10
    REQUIRED_COLUMNS = {
        "timestamp_utc",
        "agent_name",
        "rule_id",
        "rule_level",
        "rule_firedtimes",
        "event_id",
        "source_ip",
        "dst_user",
        "src_ip",
        "target_user_name",
        "rule_description",
    }

    @classmethod
    def load_dataset(cls, file_path):
        """Read the cleaned CSV and create only the features needed by EDA."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy dataset sạch: {path}")

        string_columns = {
            "agent_name": "string",
            "rule_id": "string",
            "event_id": "string",
            "source_ip": "string",
            "dst_user": "string",
            "src_ip": "string",
            "target_user_name": "string",
            "rule_description": "string",
        }
        frame = pd.read_csv(path, dtype=string_columns, low_memory=False)
        missing = cls.REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(
                "CSV thiếu cột cho Tầng 2: " + ", ".join(sorted(missing))
            )

        frame["timestamp_utc"] = pd.to_datetime(
            frame["timestamp_utc"], format="mixed", errors="coerce", utc=True
        )
        frame["rule_level"] = pd.to_numeric(
            frame["rule_level"], errors="coerce"
        ).astype("Int64")
        frame["rule_firedtimes"] = pd.to_numeric(
            frame["rule_firedtimes"], errors="coerce"
        ).astype("Int64")
        frame = frame.dropna(
            subset=["timestamp_utc", "agent_name", "rule_id", "rule_level"]
        ).copy()

        # Windows and non-Windows logs store source/user values in different fields.
        # Keep the original columns and add combined analysis-only features.
        frame["analysis_source_ip"] = frame["source_ip"].fillna(frame["src_ip"])
        frame["analysis_user"] = frame["target_user_name"].fillna(
            frame["dst_user"]
        )
        frame["event_date"] = frame["timestamp_utc"].dt.floor("D")
        return frame.sort_values("timestamp_utc").reset_index(drop=True)

    @staticmethod
    def metadata(frame):
        """Return the actual temporal coverage and dataset size."""
        if frame.empty:
            return {
                "rows": 0,
                "agents": 0,
                "minimum_timestamp": None,
                "maximum_timestamp": None,
                "coverage_days": 0,
            }
        minimum = frame["timestamp_utc"].min()
        maximum = frame["timestamp_utc"].max()
        coverage_days = max(1, int((maximum - minimum).total_seconds() / 86400) + 1)
        return {
            "rows": int(len(frame)),
            "agents": int(frame["agent_name"].nunique()),
            "minimum_timestamp": minimum,
            "maximum_timestamp": maximum,
            "coverage_days": coverage_days,
        }

    @classmethod
    def filter_data(
        cls,
        frame,
        agent=ALL_AGENTS,
        days=30,
        alert_level=ALL_LEVELS,
        specific_date=None,
        start_date=None,
        end_date=None,
    ):
        """Lọc theo một ngày, khoảng ngày bao gồm hai đầu hoặc N ngày gần nhất.

        N ngày được tính từ ngày lớn nhất trong file, không từ ngày hệ thống;
        vì vậy dataset lịch sử vẫn cho kết quả đúng.
        """
        if frame.empty:
            return frame.copy(), cls.metadata(frame)

        days = int(days)
        maximum = frame["timestamp_utc"].max()
        if specific_date not in (None, ""):
            try:
                selected_date = pd.Timestamp(specific_date)
            except (TypeError, ValueError) as error:
                raise ValueError(f"Ngày cụ thể không hợp lệ: {specific_date}") from error
            if selected_date.tzinfo is None:
                selected_date = selected_date.tz_localize("UTC")
            else:
                selected_date = selected_date.tz_convert("UTC")
            start = selected_date.floor("D")
            end_exclusive = start + pd.Timedelta(days=1)
            result = frame[
                (frame["timestamp_utc"] >= start)
                & (frame["timestamp_utc"] < end_exclusive)
            ]
            filter_end = start
            filter_mode = "specific_date"
        elif start_date not in (None, "") or end_date not in (None, ""):
            if start_date in (None, "") or end_date in (None, ""):
                raise ValueError("Phải chọn đủ ngày bắt đầu và ngày kết thúc.")
            try:
                start = pd.Timestamp(start_date)
                end = pd.Timestamp(end_date)
            except (TypeError, ValueError) as error:
                raise ValueError("Khoảng thời gian không hợp lệ.") from error
            if start.tzinfo is None:
                start = start.tz_localize("UTC")
            else:
                start = start.tz_convert("UTC")
            if end.tzinfo is None:
                end = end.tz_localize("UTC")
            else:
                end = end.tz_convert("UTC")
            start = start.floor("D")
            end = end.floor("D")
            if start > end:
                raise ValueError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")
            end_exclusive = end + pd.Timedelta(days=1)
            result = frame[
                (frame["timestamp_utc"] >= start)
                & (frame["timestamp_utc"] < end_exclusive)
            ]
            filter_end = end
            filter_mode = "date_range"
        else:
            if days < 1:
                raise ValueError("Số ngày gần nhất phải từ 1 trở lên.")
            filter_end = maximum.floor("D")
            start = filter_end - pd.Timedelta(days=days - 1)
            end_exclusive = filter_end + pd.Timedelta(days=1)
            result = frame[
                (frame["timestamp_utc"] >= start)
                & (frame["timestamp_utc"] < end_exclusive)
            ]
            filter_mode = "period"
        if agent and agent != cls.ALL_AGENTS:
            result = result[result["agent_name"] == agent]
        if alert_level not in (None, "", cls.ALL_LEVELS):
            try:
                selected_level = int(alert_level)
            except (TypeError, ValueError) as error:
                raise ValueError(f"Alert Level không hợp lệ: {alert_level}") from error
            result = result[result["rule_level"] == selected_level]

        result = result.copy()
        details = cls.metadata(frame)
        details.update(
            {
                "requested_days": days,
                "filter_start": max(start, frame["timestamp_utc"].min()),
                "filter_end": min(filter_end, frame["event_date"].max()),
                "range_limited": (
                    filter_mode == "period" and days > details["coverage_days"]
                ),
                "selected_agent": agent,
                "selected_alert_level": alert_level,
                "selected_date": start.date().isoformat()
                if filter_mode == "specific_date"
                else None,
                "selected_start_date": start.date().isoformat()
                if filter_mode == "date_range"
                else None,
                "selected_end_date": end.date().isoformat()
                if filter_mode == "date_range"
                else None,
                "filter_mode": filter_mode,
            }
        )
        result.attrs.update(details)
        return result, details

    @staticmethod
    def overview(frame):
        """Calculate descriptive statistics from the filtered event rows."""
        daily = frame.groupby("event_date").size() if not frame.empty else pd.Series()
        return {
            "total_alerts": int(len(frame)),
            "agents": int(frame["agent_name"].nunique()) if not frame.empty else 0,
            "unique_rules": int(frame["rule_id"].nunique()) if not frame.empty else 0,
            "unique_event_ids": int(frame["event_id"].nunique()) if not frame.empty else 0,
            "unique_source_ips": int(frame["analysis_source_ip"].nunique())
            if not frame.empty
            else 0,
            "unique_users": int(frame["analysis_user"].nunique())
            if not frame.empty
            else 0,
            "mean_alerts_per_day": float(daily.mean()) if not daily.empty else 0.0,
            "median_alerts_per_day": float(daily.median()) if not daily.empty else 0.0,
        }

    @staticmethod
    def daily_counts(frame):
        """Đếm số alert theo từng ngày để vẽ biểu đồ xu hướng."""
        if frame.empty:
            return pd.Series(dtype="int64")
        return frame.groupby("event_date").size().sort_index()

    @staticmethod
    def level_counts(frame):
        """Đếm số alert theo rule_level để vẽ phân bố level."""
        if frame.empty:
            return pd.Series(dtype="int64")
        return frame["rule_level"].value_counts().sort_index()

    @staticmethod
    def agent_high_level_counts(frame, minimum_level=10):
        """Count logs by Agent for every integer Level from the minimum upward."""
        if frame.empty:
            return pd.DataFrame(dtype="int64")

        levels = pd.to_numeric(frame["rule_level"], errors="coerce").dropna()
        if levels.empty or int(levels.max()) < minimum_level:
            return pd.DataFrame(index=sorted(frame["agent_name"].dropna().unique()))

        maximum_level = int(levels.max())
        level_columns = list(range(minimum_level, maximum_level + 1))
        agents = sorted(frame["agent_name"].dropna().unique())
        high = frame[pd.to_numeric(frame["rule_level"], errors="coerce") >= minimum_level]
        grouped = high.groupby(["agent_name", "rule_level"]).size().unstack(fill_value=0)
        grouped.columns = grouped.columns.astype(int)
        return grouped.reindex(
            index=agents,
            columns=level_columns,
            fill_value=0,
        ).astype("int64")

    @staticmethod
    def agent_level_counts(frame):
        """Đếm Agent × mọi Alert Level thực tế để làm dữ liệu heatmap.

        KỸ THUẬT: groupby + unstack + reindex; tổ hợp không có log được điền 0.
        Không cố định level 10-13 nên heatmap luôn phản ánh đủ level trong file.
        """
        if frame.empty:
            return pd.DataFrame(dtype="int64")

        data = frame[["agent_name", "rule_level"]].copy()
        data["rule_level"] = pd.to_numeric(
            data["rule_level"], errors="coerce"
        )
        data = data.dropna(subset=["agent_name", "rule_level"])
        if data.empty:
            return pd.DataFrame(dtype="int64")

        data["rule_level"] = data["rule_level"].astype(int)
        agents = sorted(data["agent_name"].astype(str).unique())
        levels = sorted(data["rule_level"].unique())
        grouped = data.groupby(["agent_name", "rule_level"]).size().unstack(fill_value=0)
        return grouped.reindex(
            index=agents,
            columns=levels,
            fill_value=0,
        ).astype("int64")

    @staticmethod
    def top_rules(frame, limit=8):
        """Rank Rule IDs and attach their most frequent description."""
        columns = ["rule_id", "rule_description", "alert_count"]
        if frame.empty:
            return pd.DataFrame(columns=columns)

        counts = frame.groupby("rule_id", dropna=False).size().rename("alert_count")
        descriptions = frame.groupby("rule_id")["rule_description"].agg(
            lambda values: values.mode().iloc[0] if not values.mode().empty else ""
        )
        result = pd.concat([descriptions, counts], axis=1)
        return (
            result.nlargest(limit, "alert_count")
            .reset_index()[columns]
        )

    @staticmethod
    def top_agents(frame, limit=8):
        """Trả các Agent có số alert cao nhất theo thứ tự giảm dần."""
        if frame.empty:
            return pd.Series(dtype="int64")
        return frame["agent_name"].value_counts().head(limit)

    @staticmethod
    def top_event_ids(frame, limit=8):
        """Trả các Event ID xuất hiện nhiều nhất sau khi lọc."""
        if frame.empty:
            return pd.Series(dtype="int64")
        return frame["event_id"].dropna().value_counts().head(limit)

    @classmethod
    def aggregate_agent_day(cls, frame):
        """Tổng hợp alert thành đơn vị Agent/ngày dùng cho EDA và mô hình.

        KỸ THUẬT: groupby với size, sum, nunique, mean và max. Các tổ hợp
        Agent/ngày không log được tái lập để chuỗi thời gian liên tục, nhưng sẽ
        bị loại khỏi huấn luyện vì đó là dòng giữ chỗ chứ không phải quan sát.
        """
        columns = [
            "agent_name",
            "event_date",
            "total_events",
            "high_level_alerts",
            "level_11_plus_alerts",
            "level_0_7_events",
            "level_8_10_events",
            "level_above_10_events",
            "unique_rules",
            "unique_event_ids",
            "unique_source_ips",
            "unique_users",
            "avg_rule_level",
            "max_rule_level",
        ]
        if frame.empty:
            return pd.DataFrame(columns=columns)

        data = frame.copy()
        data["is_high_level"] = (
            data["rule_level"] >= cls.HIGH_LEVEL_MIN
        ).astype("int64")
        data["is_level_11_plus"] = (data["rule_level"] >= 11).astype("int64")
        data["is_level_0_7"] = data["rule_level"].between(0, 7).astype("int64")
        # Level 7 is counted only in the first interval; the next starts at 8.
        data["is_level_8_10"] = data["rule_level"].between(8, 10).astype("int64")
        data["is_level_above_10"] = (data["rule_level"] > 10).astype("int64")
        result = (
            data.groupby(["agent_name", "event_date"], dropna=False)
            .agg(
                total_events=("rule_id", "size"),
                high_level_alerts=("is_high_level", "sum"),
                level_11_plus_alerts=("is_level_11_plus", "sum"),
                level_0_7_events=("is_level_0_7", "sum"),
                level_8_10_events=("is_level_8_10", "sum"),
                level_above_10_events=("is_level_above_10", "sum"),
                unique_rules=("rule_id", "nunique"),
                unique_event_ids=("event_id", "nunique"),
                unique_source_ips=("analysis_source_ip", "nunique"),
                unique_users=("analysis_user", "nunique"),
                avg_rule_level=("rule_level", "mean"),
                max_rule_level=("rule_level", "max"),
            )
            .reset_index()
        )

        # A missing Agent/day combination means zero alerts, not an absent sample.
        start = pd.Timestamp(
            frame.attrs.get("filter_start", frame["event_date"].min())
        ).floor("D")
        end = pd.Timestamp(
            frame.attrs.get("filter_end", frame["event_date"].max())
        ).floor("D")
        complete_index = pd.MultiIndex.from_product(
            [
                sorted(frame["agent_name"].dropna().unique()),
                pd.date_range(start, end, freq="D", tz="UTC"),
            ],
            names=["agent_name", "event_date"],
        )
        result = result.set_index(["agent_name", "event_date"]).reindex(complete_index)
        count_columns = [
            "total_events",
            "high_level_alerts",
            "level_11_plus_alerts",
            "level_0_7_events",
            "level_8_10_events",
            "level_above_10_events",
            "unique_rules",
            "unique_event_ids",
            "unique_source_ips",
            "unique_users",
        ]
        result[count_columns] = result[count_columns].fillna(0).astype("int64")
        result = result.reset_index()
        return result[columns].sort_values(["event_date", "agent_name"])
