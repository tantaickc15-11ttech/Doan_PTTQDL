"""Cửa sổ danh sách alert chi tiết sau khi áp dụng bộ lọc EDA.

KỸ THUẬT: lazy loading theo batch và chỉ dựng JSON khi người dùng chọn dòng.
VẤN ĐỀ: Treeview chứa quá nhiều alert sẽ chậm và tốn bộ nhớ.
TÁC DỤNG: xem chi tiết mà vẫn giữ giao diện phản hồi tốt.
"""

import json
import tkinter as tk
from tkinter import ttk

import pandas as pd



class FilteredAlertWindow(tk.Toplevel):
    """Display filtered alerts in batches without inserting every row at once."""

    BATCH_SIZE = 20
    DETAIL_COLUMNS = (
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
    )

    def __init__(self, parent, frame, filter_description=""):
        """Tạo cửa sổ và giữ DataFrame đã lọc để nạp theo batch."""
        super().__init__(parent)
        self.frame = frame.iloc[::-1]
        self.loaded_rows = 0
        self.load_scheduled = False

        self.title("Danh sách Alert theo bộ lọc")
        self.geometry("1250x700")
        self.minsize(900, 500)

        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Danh sách Alert",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        right_header = ttk.Frame(header)
        right_header.pack(side="right")
        ttk.Label(right_header, text=filter_description).pack(anchor="e")
        self.state_var = tk.StringVar(value="Chưa tải dữ liệu")
        ttk.Label(right_header, textvariable=self.state_var).pack(anchor="e")

        table_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        table_frame.pack(fill="both", expand=True)
        columns = (
            "timestamp",
            "agent",
            "ip",
            "user",
            "event_id",
            "rule",
            "level",
            "firedtimes",
            "description",
        )
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "timestamp": "Thời gian UTC",
            "agent": "Agent",
            "ip": "IP nguồn",
            "user": "Người dùng",
            "event_id": "Event ID",
            "rule": "Rule ID",
            "level": "Level",
            "firedtimes": "Fired times",
            "description": "Mô tả",
        }
        widths = {
            "timestamp": 190,
            "agent": 145,
            "ip": 120,
            "user": 145,
            "event_id": 80,
            "rule": 80,
            "level": 55,
            "firedtimes": 85,
            "description": 360,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")

        self.vertical_scrollbar = ttk.Scrollbar(
            table_frame, orient="vertical", command=self.tree.yview
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(
            yscrollcommand=self._on_scroll,
            xscrollcommand=horizontal_scrollbar.set,
        )
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Double-1>", self._show_detail)

        self._load_next_batch()

    def _load_next_batch(self):
        """Chèn batch tiếp theo và giữ ánh xạ từ item UI về dòng dữ liệu."""
        self.load_scheduled = False
        if self.loaded_rows >= len(self.frame):
            return

        start = self.loaded_rows
        end = min(start + self.BATCH_SIZE, len(self.frame))
        for position in range(start, end):
            row = self.frame.iloc[position]
            source_ip = self._first_value(row.get("source_ip"), row.get("src_ip"))
            user = self._first_value(
                row.get("target_user_name"), row.get("dst_user")
            )
            self.tree.insert(
                "",
                "end",
                iid=f"alert-{position}",
                values=(
                    self._display_value(row.get("timestamp_utc")),
                    self._display_value(row.get("agent_name")),
                    source_ip,
                    user,
                    self._display_value(row.get("event_id")),
                    self._display_value(row.get("rule_id")),
                    self._display_value(row.get("rule_level")),
                    self._display_value(row.get("rule_firedtimes")),
                    self._display_value(row.get("rule_description")),
                ),
            )

        self.loaded_rows = end
        suffix = " - đã hết dữ liệu" if end >= len(self.frame) else ""
        self.state_var.set(
            f"Đã tải {self.loaded_rows:,} / {len(self.frame):,} Alert{suffix}"
            .replace(",", ".")
        )

    def _on_scroll(self, first, last):
        """Nạp thêm alert khi người dùng cuộn đến gần cuối bảng."""
        self.vertical_scrollbar.set(first, last)
        if (
            float(last) >= 0.98
            and self.loaded_rows < len(self.frame)
            and not self.load_scheduled
        ):
            self.load_scheduled = True
            self.after_idle(self._load_next_batch)

    def _show_detail(self, event):
        """Hiển thị toàn bộ trường JSON của alert được nhấp chọn."""
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        position = int(item_id.rsplit("-", 1)[1])
        row = self.frame.iloc[position]
        details = {
            column: self._json_value(row.get(column)) for column in self.DETAIL_COLUMNS
        }

        window = tk.Toplevel(self)
        window.title(f"Chi tiết log - Rule {details.get('rule_id', '')}")
        window.geometry("760x600")
        text = tk.Text(window, wrap="word", padx=12, pady=12)
        text.pack(fill="both", expand=True)
        text.insert("end", json.dumps(details, ensure_ascii=False, indent=2))
        text.configure(state="disabled")

    @classmethod
    def _first_value(cls, first, second):
        """Chọn giá trị đầu tiên không thiếu giữa hai trường tương đương."""
        first_text = cls._display_value(first)
        return first_text if first_text else cls._display_value(second)

    @staticmethod
    def _display_value(value):
        """Đổi missing thành chuỗi rỗng để trình bày trong Treeview."""
        if value is None or pd.isna(value):
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    @classmethod
    def _json_value(cls, value):
        """Chuyển kiểu pandas thành kiểu có thể serialize sang JSON."""
        if value is None or pd.isna(value):
            return ""
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if hasattr(value, "item"):
            return value.item()
        return value
