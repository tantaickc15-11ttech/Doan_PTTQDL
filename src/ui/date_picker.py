"""Bộ chọn ngày cho bộ lọc EDA.

KỸ THUẬT: dựng lịch bằng thư viện chuẩn ``calendar`` và Tkinter.
TÁC DỤNG: giới hạn lựa chọn trong khoảng ngày thật sự có trong dataset.
"""

import calendar
import tkinter as tk
from datetime import date
from tkinter import ttk


class DatePickerPopup(tk.Toplevel):
    """Display a month calendar and return one date through a callback."""

    WEEKDAYS = ("T2", "T3", "T4", "T5", "T6", "T7", "CN")

    def __init__(
        self,
        parent,
        anchor,
        initial_date,
        minimum_date,
        maximum_date,
        on_select,
    ):
        """Khởi tạo popup, phạm vi ngày hợp lệ và callback nhận kết quả."""
        super().__init__(parent)
        self.minimum_date = minimum_date
        self.maximum_date = maximum_date
        self.on_select = on_select
        self.year = initial_date.year
        self.month = initial_date.month

        self.title("Chọn ngày")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.header = ttk.Frame(self, padding=(6, 6, 6, 2))
        self.header.pack(fill="x")
        self.previous_button = ttk.Button(
            self.header, text="‹", width=3, command=lambda: self._move_month(-1)
        )
        self.previous_button.pack(side="left")
        self.month_label = ttk.Label(self.header, anchor="center", width=18)
        self.month_label.pack(side="left", fill="x", expand=True, padx=4)
        self.next_button = ttk.Button(
            self.header, text="›", width=3, command=lambda: self._move_month(1)
        )
        self.next_button.pack(side="right")

        self.calendar_frame = ttk.Frame(self, padding=(6, 2, 6, 6))
        self.calendar_frame.pack(fill="both", expand=True)
        self._render_month()

        self.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height()
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.focus_set()

    def _render_month(self):
        """Vẽ lại lưới ngày và khóa ngày nằm ngoài phạm vi dữ liệu."""
        for child in self.calendar_frame.winfo_children():
            child.destroy()

        self.month_label.configure(text=f"Tháng {self.month:02d}/{self.year}")
        for column, weekday in enumerate(self.WEEKDAYS):
            ttk.Label(
                self.calendar_frame, text=weekday, anchor="center", width=4
            ).grid(row=0, column=column, padx=1, pady=1)

        month_rows = calendar.Calendar(firstweekday=0).monthdayscalendar(
            self.year, self.month
        )
        for row, week in enumerate(month_rows, start=1):
            for column, day_number in enumerate(week):
                if day_number == 0:
                    ttk.Label(self.calendar_frame, text="", width=4).grid(
                        row=row, column=column, padx=1, pady=1
                    )
                    continue
                candidate = date(self.year, self.month, day_number)
                state = (
                    "normal"
                    if self.minimum_date <= candidate <= self.maximum_date
                    else "disabled"
                )
                ttk.Button(
                    self.calendar_frame,
                    text=str(day_number),
                    width=4,
                    state=state,
                    command=lambda value=candidate: self._choose(value),
                ).grid(row=row, column=column, padx=1, pady=1)

        current_month = self.year * 12 + self.month
        minimum_month = self.minimum_date.year * 12 + self.minimum_date.month
        maximum_month = self.maximum_date.year * 12 + self.maximum_date.month
        self.previous_button.configure(
            state="normal" if current_month > minimum_month else "disabled"
        )
        self.next_button.configure(
            state="normal" if current_month < maximum_month else "disabled"
        )

    def _move_month(self, offset):
        """Chuyển tháng đang hiển thị rồi vẽ lại lịch."""
        month_index = self.year * 12 + self.month - 1 + offset
        self.year, zero_based_month = divmod(month_index, 12)
        self.month = zero_based_month + 1
        self._render_month()

    def _choose(self, selected_date):
        """Trả ngày hợp lệ qua callback và đóng popup."""
        self.on_select(selected_date)
        self.destroy()
