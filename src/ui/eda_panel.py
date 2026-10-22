"""Giao diện EDA mô tả, ngoại lệ và mối liên hệ giữa biến.

KỸ THUẬT: lọc tương tác, Matplotlib/Seaborn và worker thread khi nạp.
VẤN ĐỀ: nhiều biểu đồ phải dùng cùng tập con mà không khóa Tkinter.
TÁC DỤNG: biến kết quả từ các service thành bằng chứng EDA trực quan.
"""

import queue
import threading
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
import seaborn as sns

from src.services.eda_service import EdaService
from src.services.outlier_service import OutlierService
from src.services.relationship_service import RelationshipService
from src.ui.date_picker import DatePickerPopup
from src.ui.filtered_alert_window import FilteredAlertWindow


class EdaPanel(ttk.Frame):
    """Present Tầng 2 results calculated from wazuh_cleaned.csv."""

    DATE_MODE_7_DAYS = "7 ngày gần nhất"
    DATE_MODE_14_DAYS = "14 ngày gần nhất"
    DATE_MODE_30_DAYS = "30 ngày gần nhất"
    DATE_MODE_RANGE = "Khoảng thời gian"
    DATE_MODE_SINGLE = "Một ngày cụ thể"
    RECENT_DAY_MODES = {
        DATE_MODE_7_DAYS: 7,
        DATE_MODE_14_DAYS: 14,
        DATE_MODE_30_DAYS: 30,
    }
    ANOVA_TARGET = "total_events"
    ANOVA_LABEL = "Tổng số Event/ngày"
    AGENT_COLOR_MAP = {
        "SVR_Zabbix01": "#1F4E79",
        "SVDB01": "#D62728",
        "SVRAD003": "#5DA5DA",
        "SVRAD001": "#2CA02C",
    }
    FALLBACK_AGENT_COLORS = ("#9467BD", "#8C564B", "#17BECF", "#7F7F7F")

    def __init__(self, parent, csv_path, analysis_parent=None):
        """Khởi tạo dữ liệu, trạng thái bộ lọc và các vùng biểu đồ EDA."""
        super().__init__(parent, padding=8)
        self.csv_path = csv_path
        self.analysis_parent = analysis_parent
        self.dataset = None
        self.filtered = None
        self.daily_summary = None
        self.anova_summary = None
        self.overview_total_events_by_agent = pd.Series(dtype="float64")
        self.load_queue = queue.Queue()
        self.load_thread = None
        self.poll_after_id = None
        self._create_filters()
        self._create_content()
        self.reload_dataset()

    def _create_filters(self):
        """Tạo bộ lọc thời gian, Agent, level và nút áp dụng."""
        filters = ttk.LabelFrame(self, text="Bộ lọc chung", padding=8)
        filters.pack(fill="x", pady=(0, 8))

        ttk.Label(filters, text="Agent:").pack(side="left")
        self.agent_var = tk.StringVar(value=EdaService.ALL_AGENTS)
        self.agent_box = ttk.Combobox(
            filters,
            textvariable=self.agent_var,
            values=[EdaService.ALL_AGENTS],
            state="readonly",
            width=22,
        )
        self.agent_box.pack(side="left", padx=(5, 15))

        ttk.Label(filters, text="Thời gian:").pack(side="left")
        self.date_mode_var = tk.StringVar(value=self.DATE_MODE_30_DAYS)
        self.date_mode_box = ttk.Combobox(
            filters,
            textvariable=self.date_mode_var,
            values=[
                self.DATE_MODE_7_DAYS,
                self.DATE_MODE_14_DAYS,
                self.DATE_MODE_30_DAYS,
                self.DATE_MODE_RANGE,
                self.DATE_MODE_SINGLE,
            ],
            state="readonly",
            width=18,
        )
        self.date_mode_box.pack(side="left", padx=(5, 8))
        self.date_mode_box.bind("<<ComboboxSelected>>", self._on_date_mode_changed)

        self.start_date_var = tk.StringVar(value="-")
        self.end_date_var = tk.StringVar(value="-")
        self.specific_date_var = tk.StringVar(value="-")
        ttk.Label(filters, text="Từ:").pack(side="left")
        self.start_date_button = ttk.Button(
            filters,
            textvariable=self.start_date_var,
            width=11,
            command=lambda: self._open_date_picker(
                self.start_date_button, self.start_date_var
            ),
        )
        self.start_date_button.pack(side="left", padx=(4, 6))
        ttk.Label(filters, text="Đến:").pack(side="left")
        self.end_date_button = ttk.Button(
            filters,
            textvariable=self.end_date_var,
            width=11,
            command=lambda: self._open_date_picker(
                self.end_date_button, self.end_date_var
            ),
        )
        self.end_date_button.pack(side="left", padx=(4, 6))
        ttk.Label(filters, text="Ngày:").pack(side="left")
        self.specific_date_button = ttk.Button(
            filters,
            textvariable=self.specific_date_var,
            width=11,
            command=lambda: self._open_date_picker(
                self.specific_date_button, self.specific_date_var
            ),
        )
        self.specific_date_button.pack(side="left", padx=(4, 6))

        ttk.Label(filters, text="Alert Level:").pack(side="left", padx=(15, 0))
        self.level_var = tk.StringVar(value=EdaService.ALL_LEVELS)
        self.level_box = ttk.Combobox(
            filters,
            textvariable=self.level_var,
            values=[EdaService.ALL_LEVELS],
            state="readonly",
            width=10,
        )
        self.level_box.pack(side="left", padx=(5, 0))
        self.apply_button = ttk.Button(
            filters, text="Phân tích", command=self.apply_filters, state="disabled"
        )
        self.apply_button.pack(side="left", padx=15)

        self.filter_note_var = tk.StringVar(value="Đang đọc dataset sạch...")
        ttk.Label(filters, textvariable=self.filter_note_var).pack(side="right")
        self._on_date_mode_changed()

    def _create_content(self):
        """Tạo nội dung Tổng quan và gắn phần Phân tích vào tab được cấp."""
        self.overview_tab = ttk.Frame(self, padding=6)
        self.overview_tab.pack(fill="both", expand=True)

        analysis_host = self.analysis_parent if self.analysis_parent is not None else self
        if self.analysis_parent is not None:
            self._create_analysis_filters(analysis_host)
        notebook = ttk.Notebook(analysis_host)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)
        self.outlier_tab = ttk.Frame(notebook, padding=6)
        self.relationship_tab = ttk.Frame(notebook, padding=6)
        notebook.add(self.outlier_tab, text="Độ phân tán dữ liệu")
        notebook.add(self.relationship_tab, text="Mối quan hệ biến")

        self._create_overview()
        self._create_outlier()
        self._create_relationship()

    def _create_analysis_filters(self, parent):
        """Mirror the shared filters so they remain visible on detailed EDA tabs."""
        filters = ttk.LabelFrame(parent, text="Bộ lọc chung", padding=8)
        filters.pack(fill="x", padx=8, pady=(8, 0))

        ttk.Label(filters, text="Agent:").pack(side="left")
        self.analysis_agent_box = ttk.Combobox(
            filters,
            textvariable=self.agent_var,
            values=[EdaService.ALL_AGENTS],
            state="readonly",
            width=22,
        )
        self.analysis_agent_box.pack(side="left", padx=(5, 15))

        ttk.Label(filters, text="Thời gian:").pack(side="left")
        self.analysis_date_mode_box = ttk.Combobox(
            filters,
            textvariable=self.date_mode_var,
            values=[
                self.DATE_MODE_7_DAYS,
                self.DATE_MODE_14_DAYS,
                self.DATE_MODE_30_DAYS,
                self.DATE_MODE_RANGE,
                self.DATE_MODE_SINGLE,
            ],
            state="readonly",
            width=18,
        )
        self.analysis_date_mode_box.pack(side="left", padx=(5, 8))
        self.analysis_date_mode_box.bind(
            "<<ComboboxSelected>>", self._on_date_mode_changed
        )

        ttk.Label(filters, text="Từ:").pack(side="left")
        self.analysis_start_date_button = ttk.Button(
            filters,
            textvariable=self.start_date_var,
            width=11,
            command=lambda: self._open_date_picker(
                self.analysis_start_date_button, self.start_date_var
            ),
        )
        self.analysis_start_date_button.pack(side="left", padx=(4, 6))
        ttk.Label(filters, text="Đến:").pack(side="left")
        self.analysis_end_date_button = ttk.Button(
            filters,
            textvariable=self.end_date_var,
            width=11,
            command=lambda: self._open_date_picker(
                self.analysis_end_date_button, self.end_date_var
            ),
        )
        self.analysis_end_date_button.pack(side="left", padx=(4, 6))
        ttk.Label(filters, text="Ngày:").pack(side="left")
        self.analysis_date_button = ttk.Button(
            filters,
            textvariable=self.specific_date_var,
            width=11,
            command=lambda: self._open_date_picker(
                self.analysis_date_button, self.specific_date_var
            ),
        )
        self.analysis_date_button.pack(side="left", padx=(4, 6))

        ttk.Label(filters, text="Alert Level:").pack(side="left", padx=(15, 0))
        self.analysis_level_box = ttk.Combobox(
            filters,
            textvariable=self.level_var,
            values=[EdaService.ALL_LEVELS],
            state="readonly",
            width=10,
        )
        self.analysis_level_box.pack(side="left", padx=(5, 0))
        self.analysis_apply_button = ttk.Button(
            filters, text="Phân tích", command=self.apply_filters, state="disabled"
        )
        self.analysis_apply_button.pack(side="left", padx=15)
        ttk.Label(filters, textvariable=self.filter_note_var).pack(side="right")
        self._on_date_mode_changed()

    def _open_date_picker(self, anchor, target_variable):
        """Mở lịch giới hạn theo phạm vi ngày thực có trong dataset."""
        if self.dataset is None or self.dataset.empty:
            return
        minimum_date = self.dataset["timestamp_utc"].min().date()
        maximum_date = self.dataset["timestamp_utc"].max().date()
        try:
            initial_date = date.fromisoformat(target_variable.get())
        except ValueError:
            initial_date = maximum_date
        DatePickerPopup(
            self,
            anchor,
            initial_date,
            minimum_date,
            maximum_date,
            lambda selected: target_variable.set(selected.isoformat()),
        )

    def _on_date_mode_changed(self, _event=None):
        """Bật đúng ô ngày theo chế độ gần nhất, khoảng ngày hoặc một ngày."""
        selected_mode = self.date_mode_var.get()
        range_state = "normal" if selected_mode == self.DATE_MODE_RANGE else "disabled"
        single_state = (
            "normal" if selected_mode == self.DATE_MODE_SINGLE else "disabled"
        )
        for name in (
            "start_date_button",
            "end_date_button",
            "analysis_start_date_button",
            "analysis_end_date_button",
        ):
            if hasattr(self, name):
                getattr(self, name).configure(state=range_state)
        for name in ("specific_date_button", "analysis_date_button"):
            if hasattr(self, name):
                getattr(self, name).configure(state=single_state)

    def _create_overview(self):
        """Tạo KPI và các biểu đồ tổng quan dùng chung bộ lọc."""
        cards = ttk.Frame(self.overview_tab)
        cards.pack(fill="x", pady=(0, 6))
        self.eda_cards = {}
        self.eda_card_frames = {}
        items = [
            ("total_alerts", "Tổng alert"),
            ("unique_rules", "Số Rule"),
            ("unique_source_ips", "Số IP nguồn"),
            ("unique_users", "Số user"),
        ]
        for index, (key, title) in enumerate(items):
            card = ttk.LabelFrame(cards, text=title, padding=6)
            card.grid(row=0, column=index, padx=3, sticky="nsew")
            cards.columnconfigure(index, weight=1)
            value = ttk.Label(card, text="0", font=("Segoe UI", 14, "bold"))
            value.pack()
            self.eda_cards[key] = value
            self.eda_card_frames[key] = card

            if key == "total_alerts":
                card.configure(cursor="hand2")
                value.configure(cursor="hand2")
                card.bind("<Button-1>", self._open_filtered_alerts)
                value.bind("<Button-1>", self._open_filtered_alerts)
                hint = ttk.Label(card, text="Nhấn để xem", cursor="hand2")
                hint.pack()
                hint.bind("<Button-1>", self._open_filtered_alerts)

        self.overview_figure = Figure(figsize=(11, 6), dpi=90, constrained_layout=True)
        self.overview_canvas = FigureCanvasTkAgg(
            self.overview_figure, master=self.overview_tab
        )
        self.overview_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.overview_hover_items = []
        self.overview_hover_annotation = None
        self.overview_canvas.mpl_connect(
            "motion_notify_event", self._on_overview_chart_hover
        )

    def _create_outlier(self):
        """Tạo khu vực chọn chỉ số, Boxplot, KDE và bảng IQR."""
        controls = ttk.Frame(self.outlier_tab)
        controls.pack(fill="x", pady=(0, 6))
        ttk.Label(controls, text="Chỉ tiêu: Tổng số Event theo Agent/ngày").pack(
            side="left"
        )
        self.iqr_note_var = tk.StringVar(value="Chưa có kết quả")
        ttk.Label(controls, textvariable=self.iqr_note_var).pack(side="left", padx=12)

        pane = ttk.Panedwindow(self.outlier_tab, orient="vertical")
        pane.pack(fill="both", expand=True)

        upper = ttk.Frame(pane)
        lower = ttk.Frame(pane)
        pane.add(upper, weight=3)
        pane.add(lower, weight=2)

        self.outlier_figure = Figure(figsize=(9, 5), dpi=90, constrained_layout=True)
        self.outlier_canvas = FigureCanvasTkAgg(self.outlier_figure, master=upper)
        self.outlier_canvas.get_tk_widget().pack(fill="both", expand=True)

        outlier_frame = ttk.LabelFrame(lower, text="Bảng đánh giá Outlier")
        outlier_frame.pack(fill="both", expand=True)
        outlier_columns = (
            "group", "date", "agent", "q1", "q2", "q3", "iqr",
            "lower", "upper", "value", "result",
        )
        self.outlier_tree = ttk.Treeview(
            outlier_frame, columns=outlier_columns, show="headings", height=7
        )
        outlier_headings = {
            "group": "Chỉ tiêu", "date": "Ngày", "agent": "Agent",
            "q1": "Q1", "q2": "Q2 (Median)", "q3": "Q3",
            "iqr": "IQR", "lower": "Ngưỡng dưới", "upper": "Ngưỡng trên",
            "value": "Giá trị", "result": "Kết luận",
        }
        for column in outlier_columns:
            self.outlier_tree.heading(column, text=outlier_headings[column])
            self.outlier_tree.column(column, width=105, anchor="w")
        outlier_y = ttk.Scrollbar(
            outlier_frame, orient="vertical", command=self.outlier_tree.yview
        )
        outlier_x = ttk.Scrollbar(
            outlier_frame, orient="horizontal", command=self.outlier_tree.xview
        )
        self.outlier_tree.configure(yscrollcommand=outlier_y.set, xscrollcommand=outlier_x.set)
        self.outlier_tree.grid(row=0, column=0, sticky="nsew")
        outlier_y.grid(row=0, column=1, sticky="ns")
        outlier_x.grid(row=1, column=0, sticky="ew")
        outlier_frame.rowconfigure(0, weight=1)
        outlier_frame.columnconfigure(0, weight=1)

    def _create_relationship(self):
        """Tạo bảng Pearson, heatmap/scatter và khu vực ANOVA."""
        controls = ttk.Frame(self.relationship_tab)
        controls.pack(fill="x", pady=(0, 6))
        ttk.Label(controls, text="Biến tham chiếu:").pack(side="left")
        self.relationship_target_var = tk.StringVar(value=self.ANOVA_TARGET)
        self.relationship_target_box = ttk.Combobox(
            controls,
            textvariable=self.relationship_target_var,
            values=RelationshipService.NUMERIC_METRICS,
            state="readonly",
            width=24,
        )
        self.relationship_target_box.pack(side="left", padx=6)
        self.relationship_target_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._update_relationships(redraw_fixed=True),
        )

        anova_controls = ttk.Frame(self.relationship_tab)
        anova_controls.pack(fill="x", pady=(0, 6))
        ttk.Label(
            anova_controls,
            text=f"Chỉ tiêu ANOVA: {self.ANOVA_LABEL}",
        ).pack(side="left")
        self.anova_var = tk.StringVar(value="ANOVA: chưa có kết quả")
        ttk.Label(anova_controls, textvariable=self.anova_var).pack(
            side="left", padx=12
        )

        body = ttk.Panedwindow(self.relationship_tab, orient="horizontal")
        body.pack(fill="both", expand=True)
        table_frame = ttk.LabelFrame(body, text="Bằng chứng tương quan", padding=5)
        chart_frame = ttk.Frame(body)
        body.add(table_frame, weight=3)
        body.add(chart_frame, weight=2)

        def keep_relationship_ratio(event):
            """Keep evidence/ANOVA and relationship charts at a 60/40 ratio."""
            if event.width > 1:
                body.sashpos(0, round(event.width * 0.60))

        body.bind("<Configure>", keep_relationship_ratio, add="+")

        columns = ("variable", "correlation", "absolute", "p_value", "conclusion")
        self.relationship_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", height=8
        )
        headings = {
            "variable": "Biến",
            "correlation": "Hệ số",
            "absolute": "|Hệ số|",
            "p_value": "P-value",
            "conclusion": "Kết luận",
        }
        for column in columns:
            self.relationship_tree.heading(column, text=headings[column])
            widths = {
                "variable": 105,
                "correlation": 75,
                "absolute": 75,
                "p_value": 100,
                "conclusion": 260,
            }
            width = widths[column]
            self.relationship_tree.column(column, width=width, anchor="w")
        self.relationship_tree.pack(fill="x")

        self.anova_figure = Figure(
            figsize=(5.5, 4), dpi=90, constrained_layout=True
        )
        self.anova_canvas = FigureCanvasTkAgg(
            self.anova_figure, master=table_frame
        )
        self.anova_canvas.get_tk_widget().pack(
            fill="both", expand=True, pady=(6, 0)
        )

        self.relationship_figure = Figure(
            figsize=(10, 7), dpi=90, constrained_layout=True
        )
        self.relationship_canvas = FigureCanvasTkAgg(
            self.relationship_figure, master=chart_frame
        )
        self.relationship_canvas.get_tk_widget().pack(fill="both", expand=True)

        ttk.Label(
            self.relationship_tab,
            text=(
                "Tương quan/ANOVA chỉ cho thấy mối liên hệ thống kê; "
                "không chứng minh quan hệ nhân quả."
            ),
        ).pack(anchor="w", pady=(5, 0))

    def reload_dataset(self):
        """Nạp lại CSV ở worker thread để thao tác file không đóng băng UI."""
        if self.load_thread is not None and self.load_thread.is_alive():
            return
        self.apply_button.configure(state="disabled")
        self.filter_note_var.set("Đang đọc wazuh_cleaned.csv...")
        self.load_thread = threading.Thread(target=self._load_worker, daemon=True)
        self.load_thread.start()
        self._poll_load_queue()

    def _load_worker(self):
        """Đọc CSV ở luồng nền và chuyển kết quả/lỗi vào queue."""
        try:
            dataset = EdaService.load_dataset(self.csv_path)
            self.load_queue.put(("success", dataset, EdaService.metadata(dataset)))
        except Exception as error:
            self.load_queue.put(("error", str(error)))

    def _poll_load_queue(self):
        """Nhận kết quả nạp dữ liệu trên main thread rồi cập nhật panel."""
        try:
            message = self.load_queue.get_nowait()
        except queue.Empty:
            self.poll_after_id = self.after(200, self._poll_load_queue)
            return

        self.poll_after_id = None
        self.load_thread = None
        if message[0] == "error":
            self.filter_note_var.set("Không đọc được dataset Tầng 2")
            messagebox.showerror("Lỗi Tầng 2", message[1])
            return

        _kind, self.dataset, metadata = message
        minimum_date = self.dataset["timestamp_utc"].min().date().isoformat()
        maximum_date = self.dataset["timestamp_utc"].max().date().isoformat()
        self.start_date_var.set(minimum_date)
        self.end_date_var.set(maximum_date)
        self.specific_date_var.set(maximum_date)
        self._on_date_mode_changed()
        agents = sorted(self.dataset["agent_name"].dropna().unique().tolist())
        levels = sorted(
            int(value) for value in self.dataset["rule_level"].dropna().unique()
        )
        self.agent_box.configure(values=[EdaService.ALL_AGENTS, *agents])
        self.level_box.configure(
            values=[EdaService.ALL_LEVELS, *[str(value) for value in levels]]
        )
        self.apply_button.configure(state="normal")
        if hasattr(self, "analysis_agent_box"):
            self.analysis_agent_box.configure(values=[EdaService.ALL_AGENTS, *agents])
            self.analysis_level_box.configure(
                values=[EdaService.ALL_LEVELS, *[str(value) for value in levels]]
            )
            self.analysis_apply_button.configure(state="normal")
        self.filter_note_var.set(
            f"{metadata['rows']:,} alert | {metadata['agents']} Agent | "
            f"{metadata['coverage_days']} ngày".replace(",", ".")
        )
        self.apply_filters()

    def apply_filters(self):
        """Lọc thời gian/Agent/level rồi cập nhật đồng bộ mọi phân tích."""
        if self.dataset is None:
            return
        try:
            selected_mode = self.date_mode_var.get()
            use_single_date = selected_mode == self.DATE_MODE_SINGLE
            use_custom_range = selected_mode == self.DATE_MODE_RANGE
            days = self.RECENT_DAY_MODES.get(selected_mode, 30)
            specific_date = self.specific_date_var.get() if use_single_date else None
            start_date = self.start_date_var.get() if use_custom_range else None
            end_date = self.end_date_var.get() if use_custom_range else None
            self.filtered, details = EdaService.filter_data(
                self.dataset,
                agent=self.agent_var.get(),
                days=days,
                alert_level=self.level_var.get(),
                specific_date=specific_date,
                start_date=start_date,
                end_date=end_date,
            )
            self.daily_summary = EdaService.aggregate_agent_day(self.filtered)
            self.anova_summary = self.daily_summary
            target_frame, _target_details = EdaService.filter_data(
                self.dataset,
                agent=EdaService.ALL_AGENTS,
                days=days,
                alert_level=EdaService.ALL_LEVELS,
                specific_date=specific_date,
                start_date=start_date,
                end_date=end_date,
            )
            target_summary = EdaService.aggregate_agent_day(target_frame)
            all_agents = sorted(self.dataset["agent_name"].dropna().unique())
            self.overview_total_events_by_agent = (
                target_summary.groupby("agent_name")["total_events"]
                .sum()
                .reindex(all_agents, fill_value=0.0)
            )
            if details["filter_mode"] == "specific_date":
                note = (
                    f"{len(self.filtered):,} alert | Agent: {self.agent_var.get()} | "
                    f"Level: {self.level_var.get()} | Ngày {details['selected_date']}"
                ).replace(",", ".")
            elif details["filter_mode"] == "date_range":
                note = (
                    f"{len(self.filtered):,} alert | Agent: {self.agent_var.get()} | "
                    f"Level: {self.level_var.get()} | "
                    f"Từ {details['selected_start_date']} đến "
                    f"{details['selected_end_date']}"
                ).replace(",", ".")
            else:
                note = (
                    f"{len(self.filtered):,} alert | Agent: {self.agent_var.get()} | "
                    f"Level: {self.level_var.get()} | {days} ngày gần nhất"
                ).replace(",", ".")
            self.filter_note_var.set(note)
            self._update_overview()
            self._update_outlier()
            self._update_relationships()
            self._update_anova()
        except (TypeError, ValueError, KeyError) as error:
            messagebox.showerror("Lỗi phân tích", str(error))

    def _update_overview(self):
        """Cập nhật chỉ số, xu hướng ngày, level, Agent và heatmap."""
        values = EdaService.overview(self.filtered)
        for key, label in self.eda_cards.items():
            value = values[key]
            text = f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"
            label.configure(text=text.replace(",", "."))

        figure = self.overview_figure
        figure.clear()
        self.overview_hover_items = []
        self.overview_hover_annotation = None
        grid = figure.add_gridspec(2, 3, width_ratios=[1.35, 1, 1])
        pie_axis = figure.add_subplot(grid[0, 0])
        daily_axis = figure.add_subplot(grid[0, 1])
        level_axis = figure.add_subplot(grid[0, 2])
        rule_axis = figure.add_subplot(grid[1, 0])
        ranking_axis = figure.add_subplot(grid[1, 1:])

        daily = EdaService.daily_counts(self.filtered)
        daily_axis.plot(daily.index, daily.values, marker="o", markersize=3)
        daily_points = daily_axis.scatter(
            daily.index, daily.values, s=28, color="#2563eb", alpha=0.75
        )

        def daily_tooltip(hit_details):
            """Tạo nội dung tooltip ngày và số alert tại điểm được rê chuột."""
            point_index = int(hit_details["ind"][0])
            date_text = daily.index[point_index].strftime("%Y-%m-%d")
            alert_count = int(daily.iloc[point_index])
            return (
                f"Ngày: {date_text}\n"
                f"Số Alert: {alert_count:,}"
            ).replace(",", ".")

        self.overview_hover_items.append((daily_points, daily_tooltip))
        daily_axis.set_title("Số alert thay đổi theo ngày")
        daily_axis.set_ylabel("Số alert")
        daily_axis.tick_params(axis="x", rotation=30)
        daily_axis.grid(alpha=0.25)

        levels = EdaService.level_counts(self.filtered)
        level_bars = level_axis.bar(
            levels.index.astype(str), levels.values, color="#d97706"
        )
        for bar, level, count in zip(level_bars, levels.index, levels.values):
            self.overview_hover_items.append(
                (bar, f"Level {level}\nSố lượng: {int(count):,}".replace(",", "."))
            )
        level_axis.set_title("Số lượng cảnh báo phân bố theo Level")
        level_axis.set_xlabel("Rule Level")
        level_axis.set_ylabel("Số alert")

        total_events_by_agent = self.overview_total_events_by_agent.sort_values()
        pie_labels = total_events_by_agent.index.tolist()
        pie_values = total_events_by_agent.astype(float).tolist()
        pie_total = sum(pie_values)
        pie_colors = [
            self.AGENT_COLOR_MAP.get(
                agent,
                self.FALLBACK_AGENT_COLORS[index % len(self.FALLBACK_AGENT_COLORS)],
            )
            for index, agent in enumerate(pie_labels)
        ]
        if pie_total:
            wedges, _texts = pie_axis.pie(
                pie_values,
                colors=pie_colors,
                startangle=90,
                radius=1.10,
                center=(0.10, -0.12),
                wedgeprops={"edgecolor": "white", "linewidth": 1},
            )
            legend_labels = [
                (
                    f"{agent}: {event_count:,.0f} Event "
                    f"({event_count / pie_total * 100:.1f}%)"
                ).replace(",", ".")
                for agent, event_count in zip(pie_labels, pie_values)
            ]
            pie_axis.legend(
                wedges,
                legend_labels,
                loc="upper left",
                bbox_to_anchor=(1.02, 0.98),
                fontsize=7,
                frameon=True,
            )
            pie_axis.set_xlim(-1.35, 1.65)
            pie_axis.set_ylim(-1.28, 1.18)
            for wedge, agent, event_count in zip(wedges, pie_labels, pie_values):
                percent = event_count / pie_total * 100
                tooltip = (
                    f"Agent: {agent}\nTổng Event: {event_count:,.0f}\n"
                    f"Tỷ trọng: {percent:.2f}%"
                ).replace(",", ".")
                self.overview_hover_items.append((wedge, tooltip))
        else:
            pie_axis.text(
                0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center",
                transform=pie_axis.transAxes,
            )
        pie_axis.set_title("Tỷ trọng tổng Event theo Agent")

        top_rules = EdaService.top_rules(self.filtered)
        rule_bars = rule_axis.barh(
            top_rules["rule_id"].astype(str)[::-1],
            top_rules["alert_count"][::-1],
            color="#2563eb",
        )
        for bar, rule_id, count in zip(
            rule_bars,
            top_rules["rule_id"].astype(str)[::-1],
            top_rules["alert_count"][::-1],
        ):
            self.overview_hover_items.append(
                (bar, f"Rule {rule_id}\nSố lượng: {int(count):,}".replace(",", "."))
            )
        rule_axis.set_title("Rule phát sinh nhiều Alert nhất")
        rule_axis.set_xlabel("Số alert")

        if self.agent_var.get() == EdaService.ALL_AGENTS:
            ranking = EdaService.top_agents(self.filtered)
            title = "Agent có nhiều Alert nhất"
            color = "#059669"
        else:
            ranking = EdaService.top_event_ids(self.filtered)
            title = "Event ID nào xuất hiện nhiều nhất?"
            color = "#7c3aed"
        ranking_bars = ranking_axis.barh(
            ranking.index.astype(str)[::-1], ranking.values[::-1], color=color
        )
        ranking_kind = (
            "Agent" if self.agent_var.get() == EdaService.ALL_AGENTS else "Event ID"
        )
        for bar, name, count in zip(
            ranking_bars, ranking.index.astype(str)[::-1], ranking.values[::-1]
        ):
            self.overview_hover_items.append(
                (bar, f"{ranking_kind}: {name}\nSố lượng: {int(count):,}".replace(",", "."))
            )
        ranking_axis.set_title(title)
        ranking_axis.set_xlabel("Số alert")
        self.overview_canvas.draw_idle()

    def _open_filtered_alerts(self, _event=None):
        """Mở danh sách chi tiết các alert đang thỏa bộ lọc."""
        if self.filtered is None:
            messagebox.showinfo("Danh sách Alert", "Dữ liệu EDA chưa sẵn sàng.")
            return
        description = (
            f"Agent: {self.agent_var.get()} | Level: {self.level_var.get()} | "
            + (
                f"Ngày {self.specific_date_var.get()}"
                if self.date_mode_var.get() == self.DATE_MODE_SINGLE
                else (
                    f"Từ {self.start_date_var.get()} đến {self.end_date_var.get()}"
                    if self.date_mode_var.get() == self.DATE_MODE_RANGE
                    else self.date_mode_var.get()
                )
            )
        )
        FilteredAlertWindow(self, self.filtered, description)

    def _on_overview_chart_hover(self, event):
        """Show name and count for the three categorical bar charts."""
        matched = None
        for artist, tooltip_value in self.overview_hover_items:
            contains, hit_details = artist.contains(event)
            if event.inaxes is artist.axes and contains:
                text = (
                    tooltip_value(hit_details)
                    if callable(tooltip_value)
                    else tooltip_value
                )
                matched = (artist, text)
                break

        if matched is None:
            if (
                self.overview_hover_annotation is not None
                and self.overview_hover_annotation.get_visible()
            ):
                self.overview_hover_annotation.set_visible(False)
                self.overview_canvas.draw_idle()
            return

        artist, text = matched
        axis = artist.axes
        if (
            self.overview_hover_annotation is None
            or self.overview_hover_annotation.axes is not axis
        ):
            if self.overview_hover_annotation is not None:
                self.overview_hover_annotation.set_visible(False)
            self.overview_hover_annotation = axis.annotate(
                "",
                xy=(0, 0),
                xytext=(12, 12),
                textcoords="offset points",
                bbox={"boxstyle": "round", "facecolor": "#fff7cc", "alpha": 0.95},
                arrowprops={"arrowstyle": "->", "color": "#555555"},
                annotation_clip=False,
                zorder=10,
            )
            # Tooltip chỉ phủ lên canvas, không được làm constrained_layout
            # tính lại kích thước/vị trí của các biểu đồ khi hiện hoặc ẩn.
            self.overview_hover_annotation.set_in_layout(False)
        self.overview_hover_annotation.xy = (event.xdata, event.ydata)
        self.overview_hover_annotation.set_text(text)
        self.overview_hover_annotation.set_visible(True)
        self.overview_canvas.draw_idle()

    def _update_outlier(self):
        """Hiển thị Boxplot, KDE, IQR, skewness và kurtosis."""
        if self.daily_summary is None:
            return
        results = OutlierService.analyze_total_events_by_agent(self.daily_summary)
        notes = []
        selected_one_agent = (
            self.agent_var.get() != EdaService.ALL_AGENTS and len(results) == 1
        )
        for result in results:
            note = (
                f"{result['label']}: Q2={result['q2']:.2f}, "
                f"IQR={result['iqr']:.2f}, "
                f"Outlier={result['outlier_count']}"
            )
            if selected_one_agent:
                note += (
                    f" | Skewness={result['skewness']:.4f}: "
                    f"{result['skew_conclusion']}"
                    f" | Kurtosis={result['kurtosis']:.4f}: "
                    f"{result['kurtosis_conclusion']}"
                )
            notes.append(note)
        self.iqr_note_var.set(" | ".join(notes))

        self.outlier_figure.clear()
        if results:
            grid = self.outlier_figure.add_gridspec(1, 2, width_ratios=(2.2, 1))
            palette = sns.color_palette("Set2", n_colors=len(results))
            box_axis = self.outlier_figure.add_subplot(grid[0, 0])
            box_width = 0.24 if len(results) == 1 else 0.48
            threshold_half_width = 0.16 if len(results) == 1 else 0.28
            for position, (result, color) in enumerate(
                zip(results, palette), start=1
            ):
                values = result["values"]
                if not values.empty:
                    boxplot = box_axis.boxplot(
                        [values], positions=[position], vert=True,
                        patch_artist=True, widths=box_width,
                    )
                    boxplot["boxes"][0].set_facecolor(color)
                    boxplot["boxes"][0].set_alpha(0.70)
                    box_axis.hlines(
                        result["lower_bound"],
                        position - threshold_half_width,
                        position + threshold_half_width,
                        color="#64748b", linestyle=":", linewidth=1,
                    )
                    box_axis.hlines(
                        result["upper_bound"],
                        position - threshold_half_width,
                        position + threshold_half_width,
                        color="#64748b", linestyle=":", linewidth=1,
                    )
            box_axis.set_xticks(
                range(1, len(results) + 1),
                [result["label"] for result in results],
            )
            box_axis.tick_params(axis="x", labelrotation=18, labelsize=8)
            for label in box_axis.get_xticklabels():
                label.set_horizontalalignment("right")
            box_axis.set_title("Boxplot tổng số Event theo Agent/ngày")
            box_axis.set_xlabel("Agent")
            box_axis.set_ylabel("Tổng số Event/ngày")
            box_axis.grid(axis="y", alpha=0.25)

            density_axis = self.outlier_figure.add_subplot(grid[0, 1])
            has_density = False
            for result, color in zip(results, palette):
                if len(result["density_x"]):
                    density_axis.plot(
                        result["density_x"], result["density_y"],
                        color=color, linewidth=2, label=result["label"],
                    )
                    has_density = True
                elif not result["values"].empty:
                    density_axis.axvline(
                        float(result["values"].iloc[0]), color=color,
                        linewidth=2, label=result["label"],
                    )
                    has_density = True
            if not has_density:
                density_axis.text(
                    0.5, 0.5, "Chưa có dữ liệu",
                    ha="center", va="center", transform=density_axis.transAxes,
                )
            density_axis.set_title("Mật độ tổng số Event theo Agent/ngày")
            density_axis.set_xlabel("Tổng số Event/ngày")
            density_axis.set_ylabel("Mật độ")
            density_axis.grid(alpha=0.2)
            if has_density:
                density_axis.legend(fontsize=8)
            if selected_one_agent and results and not results[0]["values"].empty:
                result = results[0]
                statistics_text = (
                    f"Skewness = {result['skewness']:.4f}\n"
                    f"{result['skew_conclusion']}\n\n"
                    f"Kurtosis = {result['kurtosis']:.4f}\n"
                    f"{result['kurtosis_conclusion']}"
                )
                density_axis.text(
                    0.98,
                    0.88,
                    statistics_text,
                    transform=density_axis.transAxes,
                    ha="right",
                    va="top",
                    fontsize=8,
                    bbox={
                        "boxstyle": "round,pad=0.45",
                        "facecolor": "white",
                        "edgecolor": "#94a3b8",
                        "alpha": 0.92,
                    },
                )
        else:
            empty_axis = self.outlier_figure.add_subplot(111)
            empty_axis.text(
                0.5, 0.5, "Chưa có dữ liệu",
                ha="center", va="center", transform=empty_axis.transAxes,
            )
            empty_axis.axis("off")

        self.outlier_canvas.draw_idle()

        for item in self.outlier_tree.get_children():
            self.outlier_tree.delete(item)
        for result in results:
            outliers = result["outliers"]
            if outliers.empty:
                self.outlier_tree.insert(
                    "", "end", values=(
                        "Tổng Event/ngày", "-", result["agent_name"],
                        f"{result['q1']:.2f}", f"{result['q2']:.2f}",
                        f"{result['q3']:.2f}",
                        f"{result['iqr']:.2f}", f"{result['lower_bound']:.2f}",
                        f"{result['upper_bound']:.2f}", "-", "-",
                    )
                )
                continue
            for row in outliers.itertuples(index=False):
                self.outlier_tree.insert(
                    "", "end", values=(
                        "Tổng Event/ngày",
                        row.event_date.strftime("%Y-%m-%d"), row.agent_name,
                        f"{result['q1']:.2f}", f"{result['q2']:.2f}",
                        f"{result['q3']:.2f}",
                        f"{result['iqr']:.2f}", f"{result['lower_bound']:.2f}",
                        f"{result['upper_bound']:.2f}", f"{row.value:.2f}",
                        row.conclusion,
                    )
                )

    def _update_relationships(self, redraw_fixed=True):
        """Hiển thị Pearson, p-value và ma trận tương quan giữa biến số."""
        if self.daily_summary is None:
            return
        target = self.relationship_target_var.get()
        evidence = RelationshipService.correlation_with(self.daily_summary, target)

        for item in self.relationship_tree.get_children():
            self.relationship_tree.delete(item)
        for row in evidence.itertuples(index=False):
            correlation_text = "-" if pd.isna(row.correlation) else f"{row.correlation:.4f}"
            absolute_text = (
                "-" if pd.isna(row.absolute_correlation)
                else f"{row.absolute_correlation:.4f}"
            )
            p_value_text = (
                "-" if pd.isna(row.p_value)
                else f"{row.p_value:.6g}".replace(".", ",")
            )
            self.relationship_tree.insert(
                "", "end", values=(
                    row.variable, correlation_text,
                    absolute_text, p_value_text,
                    row.conclusion,
                )
            )

        fixed_axes_missing = not hasattr(self, "relationship_scatter_axis")
        if redraw_fixed or fixed_axes_missing:
            full_matrix = RelationshipService.correlation_matrix(self.daily_summary)
            selected_variables = [target, *evidence.loc[evidence["selected"], "variable"]]
            selected_variables = [
                variable for variable in selected_variables
                if variable in full_matrix.columns
            ]
            matrix = full_matrix.loc[selected_variables, selected_variables]
            grouped = EdaService.agent_level_counts(self.filtered)
            self.relationship_figure.clear()
            relationship_grid = self.relationship_figure.add_gridspec(
                2,
                2,
                width_ratios=[1.0, 1.35],
                height_ratios=[1.0, 1.35],
            )
            heat_axis = self.relationship_figure.add_subplot(
                relationship_grid[0, 0]
            )
            grouped_axis = self.relationship_figure.add_subplot(
                relationship_grid[1, 0]
            )
            self.relationship_scatter_axis = self.relationship_figure.add_subplot(
                relationship_grid[:, 1]
            )
            if len(matrix.columns) >= 2:
                sns.heatmap(
                    matrix,
                    annot=False,
                    cmap="coolwarm",
                    vmin=-1,
                    vmax=1,
                    center=0,
                    linewidths=0.5,
                    square=True,
                    cbar_kws={
                        "fraction": 0.046,
                        "pad": 0.04,
                    },
                    ax=heat_axis,
                )
                heat_axis.set_xticklabels(
                    heat_axis.get_xticklabels(), rotation=90, fontsize=7
                )
                heat_axis.set_yticklabels(
                    heat_axis.get_yticklabels(), rotation=0, fontsize=7
                )
                heat_axis.set_title(
                    "Biến được chọn: |r| > 0,3 và p < 0,05"
                )
            else:
                heat_axis.text(
                    0.5,
                    0.5,
                    "Không có biến đạt\n|r| > 0,3 và p < 0,05",
                    ha="center",
                    va="center",
                    transform=heat_axis.transAxes,
                )
                heat_axis.set_axis_off()

            if not grouped.empty:
                sns.heatmap(
                    grouped,
                    annot=False,
                    cmap="Blues",
                    linewidths=1.25,
                    linecolor="white",
                    square=False,
                    cbar_kws={
                        "label": "Số lượng log",
                        "fraction": 0.06,
                        "pad": 0.04,
                    },
                    ax=grouped_axis,
                )
                grouped_axis.set_xlabel("Alert Level")
                grouped_axis.set_ylabel("Agent")
                grouped_axis.set_xticklabels(
                    grouped_axis.get_xticklabels(),
                    rotation=0,
                    fontsize=7,
                )
                grouped_axis.set_yticklabels(
                    grouped_axis.get_yticklabels(), rotation=0, fontsize=7
                )
                grouped_axis.set_title("Số log theo Agent và tất cả Level")
            else:
                grouped_axis.set_axis_off()

        scatter_axis = self.relationship_scatter_axis
        scatter_axis.clear()

        selected_evidence = evidence[evidence["selected"]]
        if not selected_evidence.empty:
            strongest = selected_evidence.iloc[0]
            other = strongest["variable"]
            scatter_axis.scatter(
                self.daily_summary[target], self.daily_summary[other], alpha=0.55, s=18
            )
            scatter_axis.set_xlabel(target)
            scatter_axis.set_ylabel(other)
            scatter_axis.set_title(
                f"{target} và {other}\n"
                f"r={strongest['correlation']:.3f} | "
                f"p={strongest['p_value']:.3g}"
            )
            scatter_axis.grid(alpha=0.2)
        else:
            scatter_axis.text(
                0.5,
                0.5,
                "Không có biến đạt điều kiện chọn",
                ha="center",
                va="center",
                transform=scatter_axis.transAxes,
            )
            scatter_axis.set_axis_off()

        self.relationship_canvas.draw_idle()

    def _update_anova(self):
        """Dùng ANOVA kiểm tra trung bình total_events có khác theo Agent."""
        if self.anova_summary is None:
            return
        metric_label = self.ANOVA_LABEL
        target = self.ANOVA_TARGET
        anova = RelationshipService.anova_by_agent(self.anova_summary, target)
        if anova["available"]:
            self.anova_var.set(
                f"ANOVA theo Agent: F={anova['f_statistic']:.4f}, "
                f"p={anova['p_value']:.6g} → {anova['conclusion']}"
            )
        else:
            self.anova_var.set(f"ANOVA: {anova['reason']}")
        self._update_anova_chart(target, metric_label, anova)

    def _update_anova_chart(self, target, metric_label, anova):
        """Visualize the daily values and group means used by one-way ANOVA."""
        self.anova_figure.clear()
        axis = self.anova_figure.add_subplot(111)
        plot_data = self.anova_summary[["agent_name", target]].copy()
        plot_data[target] = pd.to_numeric(plot_data[target], errors="coerce")
        plot_data = plot_data.dropna()

        if plot_data.empty:
            axis.text(
                0.5, 0.5, "Không có dữ liệu ANOVA",
                ha="center", va="center", transform=axis.transAxes,
            )
            axis.set_axis_off()
            self.anova_canvas.draw_idle()
            return

        means = (
            plot_data.groupby("agent_name")[target]
            .mean()
            .sort_values()
        )
        order = means.index.tolist()
        palette = {
            agent: self.AGENT_COLOR_MAP.get(
                agent,
                self.FALLBACK_AGENT_COLORS[index % len(self.FALLBACK_AGENT_COLORS)],
            )
            for index, agent in enumerate(order)
        }
        sns.stripplot(
            data=plot_data,
            x="agent_name",
            y=target,
            hue="agent_name",
            order=order,
            hue_order=order,
            jitter=0.18,
            size=4.0,
            alpha=0.65,
            palette=palette,
            legend=False,
            ax=axis,
        )
        group_stats = plot_data.groupby("agent_name")[target].agg(["min", "max"])
        group_stats = group_stats.reindex(order)
        positions = list(range(len(order)))
        line_width = 1.2
        for position, agent, minimum, maximum, mean in zip(
            positions,
            order,
            group_stats["min"],
            group_stats["max"],
            means.to_numpy(),
        ):
            color = palette[agent]
            axis.annotate(
                "",
                xy=(position, maximum),
                xytext=(position, minimum),
                arrowprops={
                    "arrowstyle": "<->",
                    "color": color,
                    "alpha": 0.9,
                    "linewidth": line_width,
                },
                zorder=1,
            )
            axis.hlines(
                mean,
                position - 0.30,
                position + 0.30,
                colors=color,
                linestyles="--",
                linewidth=line_width,
                zorder=4,
            )
        axis.plot(
            [], [], color="black", linewidth=line_width, label="Variation within"
        )
        axis.plot(
            [], [], color="black", linestyle="--",
            linewidth=line_width, label="Group Mean",
        )
        if len(order) == 2:
            lower_mean, upper_mean = sorted(means.to_numpy())
            axis.annotate(
                "",
                xy=(0.5, upper_mean),
                xytext=(0.5, lower_mean),
                arrowprops={
                    "arrowstyle": "<->",
                    "color": "#555555",
                    "linestyle": ":",
                    "linewidth": 1.2,
                },
                zorder=3,
            )
            axis.text(
                0.52,
                (lower_mean + upper_mean) / 2,
                "Variation between\nGroup means",
                fontsize=7,
                va="center",
            )
        if anova["available"]:
            title = (
                f"ANOVA theo Agent: {metric_label}\n"
                f"F={anova['f_statistic']:.3f} | p={anova['p_value']:.3g}"
            )
        else:
            title = f"ANOVA theo Agent: {metric_label}\n{anova['reason']}"
        axis.set_title(title, fontsize=9)
        axis.set_xlabel("Agent", color="black")
        axis.set_ylabel(metric_label, color="black")
        axis.tick_params(axis="both", labelsize=7, colors="black")
        axis.tick_params(axis="x", labelrotation=35)
        for spine in axis.spines.values():
            spine.set_color("black")
        for label in axis.get_xticklabels():
            label.set_horizontalalignment("right")
        axis.grid(axis="y", alpha=0.2)
        axis.legend(loc="best", fontsize=7)
        self.anova_canvas.draw_idle()
