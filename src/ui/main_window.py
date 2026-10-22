"""Cửa sổ chính điều phối toàn bộ quy trình dữ liệu và mô hình.

KỸ THUẬT: notebook, worker thread + queue và lazy loading bảng lớn.
VẤN ĐỀ: profiling/cleaning file lớn không được khóa giao diện.
TÁC DỤNG: nối raw JSON → CSV sạch → EDA → huấn luyện → kiểm thử.
"""

import json
import queue
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import pandas as pd

from src.services.cleaned_csv_reader import CleanedCsvReader
from src.services.data_cleaning_service import DataCleaningService
from src.services.data_profiling_service import DataProfilingService
from src.services.eda_service import EdaService
from src.ui.eda_panel import EdaPanel
from src.ui.external_validation_panel import ExternalValidationPanel
from src.ui.model_panel import ModelPanel


class MainWindow(tk.Tk):
    """Giao diện chính của chương trình."""

    def __init__(self):
        """Khởi tạo trạng thái ứng dụng, các tab và dữ liệu đã có trên đĩa.

        Hàm chỉ lắp ghép giao diện và gọi các bước nạp ban đầu; phép profiling,
        cleaning, EDA và mô hình được giao cho các service/panel tương ứng.
        """
        super().__init__()
        self.project_root = Path(__file__).resolve().parents[2]
        self.processing_poll_after_id = None
        self.processing_thread = None
        self.processing_queue = queue.Queue()
        self.cleaned_csv_reader = None
        self.cleaned_rows = {}
        self.cleaned_row_counter = 0
        self.cleaned_load_scheduled = False
        self.cleaned_total_rows = 0

        self.title("Wazuh Security Monitor")
        self.geometry("1200x760")
        self.minsize(1000, 650)

        self._configure_style()
        self._create_toolbar()
        self._create_notebook()
        self._create_status_bar()
        self._load_existing_quality_reports()
        self._reset_cleaned_log_reader()
        self._reload_processed_data_view()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self):
        """Thiết lập theme, font và chiều cao dòng dùng chung cho các widget."""
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("CardTitle.TLabel", font=("Segoe UI", 10))
        style.configure("CardValue.TLabel", font=("Segoe UI", 22, "bold"))
        style.configure("Treeview", rowheight=28)

    def _create_toolbar(self):
        """Tạo tiêu đề cùng nút nhập dữ liệu và làm mới toàn ứng dụng."""
        toolbar = ttk.Frame(self, padding=(12, 10))
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Wazuh Security Monitor", style="Title.TLabel").pack(
            side="left"
        )
        self.import_button = ttk.Button(
            toolbar,
            text="Thêm dữ liệu",
            command=self.import_json,
        )
        self.import_button.pack(side="right", padx=4)
        self.refresh_button = ttk.Button(
            toolbar,
            text="Làm mới",
            command=self.refresh_data_views,
        )
        self.refresh_button.pack(side="right", padx=4)

    def _create_notebook(self):
        """Tạo năm tab chính và gắn từng panel chức năng vào đúng tab.

        Đây là điểm nối UI: Tổng quan/Phân tích dùng EdaPanel, Xây dựng mô hình
        dùng ModelPanel và Kiểm thử dữ liệu mới dùng ExternalValidationPanel.
        """
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.dashboard_tab = ttk.Frame(self.notebook)
        self.data_quality_tab = ttk.Frame(self.notebook, padding=10)
        self.eda_tab = ttk.Frame(self.notebook)
        self.model_tab = ttk.Frame(self.notebook)
        self.external_validation_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.dashboard_tab, text="Tổng quan")
        self.notebook.add(self.data_quality_tab, text="Quan sát dữ liệu")
        self.notebook.add(self.eda_tab, text="Phân tích")
        self.notebook.add(self.model_tab, text="Xây dựng mô hình")
        self.notebook.add(
            self.external_validation_tab,
            text="Kiểm thử dữ liệu mới",
        )

        self._create_data_quality()
        self.eda_panel = EdaPanel(
            self.dashboard_tab,
            csv_path=self.project_root / "data" / "processed" / "wazuh_cleaned.csv",
            analysis_parent=self.eda_tab,
        )
        self.eda_panel.pack(fill="both", expand=True)
        self.model_panel = ModelPanel(
            self.model_tab,
            csv_path=self.project_root / "data" / "processed" / "wazuh_cleaned.csv",
        )
        self.model_panel.pack(fill="both", expand=True)
        self.external_validation_panel = ExternalValidationPanel(
            self.external_validation_tab,
            model_panel=self.model_panel,
        )
        self.external_validation_panel.pack(fill="both", expand=True)
        self.notebook.bind(
            "<<NotebookTabChanged>>",
            self._on_main_tab_changed,
            add="+",
        )

    def _on_main_tab_changed(self, _event=None):
        """Hide global data actions inside the independent-test tab."""
        selected_tab = self.notebook.nametowidget(self.notebook.select())
        if selected_tab is self.external_validation_tab:
            self.import_button.pack_forget()
            self.refresh_button.pack_forget()
            return

        if not self.import_button.winfo_manager():
            self.import_button.pack(side="right", padx=4)
        if not self.refresh_button.winfo_manager():
            self.refresh_button.pack(side="right", padx=4)

    def _create_data_quality(self):
        """Tạo tab Before/After cleaning và hai bảng dữ liệu ban đầu/đã xử lý."""
        self.data_quality_notebook = ttk.Notebook(self.data_quality_tab)
        self.data_quality_notebook.pack(fill="both", expand=True)

        self.initial_data_tab = ttk.Frame(self.data_quality_notebook, padding=8)
        self.processed_data_tab = ttk.Frame(self.data_quality_notebook, padding=8)
        self.data_quality_notebook.add(
            self.initial_data_tab,
            text="Dữ liệu ban đầu",
        )
        self.data_quality_notebook.add(
            self.processed_data_tab,
            text="Dữ liệu xử lý",
        )

        header = ttk.Frame(self.initial_data_tab)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Kiểm tra và làm sạch dữ liệu", style="Title.TLabel").pack(
            side="left"
        )
        self.quality_state_var = tk.StringVar(value="Chưa có kết quả")
        ttk.Label(header, textvariable=self.quality_state_var).pack(side="right")

        self.quality_file_var = tk.StringVar(value="Chưa chọn dataset")
        ttk.Label(self.initial_data_tab, textvariable=self.quality_file_var).pack(
            anchor="w", pady=(0, 6)
        )
        self.loading_var = tk.StringVar(value="")
        ttk.Label(
            self.initial_data_tab,
            textvariable=self.loading_var,
            font=("Segoe UI", 10, "italic"),
        ).pack(anchor="w", pady=(0, 10))

        cards = ttk.Frame(self.initial_data_tab)
        cards.pack(fill="x", pady=(0, 10))
        self.quality_card_values = {}
        items = [
            ("input", "Dòng đầu vào"),
            ("duplicates", "Dòng trùng ID"),
            ("output", "Dòng sạch"),
            ("retention", "Tỷ lệ giữ lại"),
        ]
        for index, (key, title) in enumerate(items):
            card = ttk.LabelFrame(cards, padding=8)
            card.grid(row=0, column=index, padx=4, sticky="nsew")
            cards.columnconfigure(index, weight=1)
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack()
            value = ttk.Label(card, text="0", font=("Segoe UI", 16, "bold"))
            value.pack(pady=(4, 0))
            self.quality_card_values[key] = value

        tables = ttk.Panedwindow(self.initial_data_tab, orient="horizontal")
        tables.pack(fill="both", expand=True, pady=(0, 8))

        reasons_frame = ttk.LabelFrame(tables, text="Nguyên nhân loại", padding=6)
        missing_frame = ttk.LabelFrame(tables, text="Missing theo trường", padding=6)
        tables.add(reasons_frame, weight=1)
        tables.add(missing_frame, weight=2)

        self.removed_tree = ttk.Treeview(
            reasons_frame,
            columns=("reason", "count"),
            show="headings",
            height=7,
        )
        self.removed_tree.heading("reason", text="Nguyên nhân")
        self.removed_tree.heading("count", text="Số dòng")
        self.removed_tree.column("reason", width=190)
        self.removed_tree.column("count", width=90, anchor="e")
        self.removed_tree.pack(fill="both", expand=True)

        self.missing_tree = ttk.Treeview(
            missing_frame,
            columns=("field", "missing", "percent"),
            show="headings",
            height=7,
        )
        self.missing_tree.heading("field", text="Trường")
        self.missing_tree.heading("missing", text="Thiếu")
        self.missing_tree.heading("percent", text="Tỷ lệ")
        self.missing_tree.column("field", width=230)
        self.missing_tree.column("missing", width=90, anchor="e")
        self.missing_tree.column("percent", width=90, anchor="e")
        missing_scrollbar = ttk.Scrollbar(
            missing_frame,
            orient="vertical",
            command=self.missing_tree.yview,
        )
        self.missing_tree.configure(yscrollcommand=missing_scrollbar.set)
        self.missing_tree.pack(side="left", fill="both", expand=True)
        missing_scrollbar.pack(side="right", fill="y")

        cleaned_frame = ttk.LabelFrame(
            self.initial_data_tab,
            text="Danh sách log sau Cleaning",
            padding=6,
        )
        cleaned_frame.pack(fill="both", expand=True)
        self.cleaned_list_state_var = tk.StringVar(value="Chưa có CSV sạch")
        ttk.Label(cleaned_frame, textvariable=self.cleaned_list_state_var).pack(
            anchor="w", pady=(0, 5)
        )

        cleaned_table_frame = ttk.Frame(cleaned_frame)
        cleaned_table_frame.pack(fill="both", expand=True)
        cleaned_columns = (
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
        self.cleaned_tree = ttk.Treeview(
            cleaned_table_frame,
            columns=cleaned_columns,
            show="headings",
            height=9,
        )
        cleaned_headings = {
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
        cleaned_widths = {
            "timestamp": 190,
            "agent": 145,
            "ip": 120,
            "user": 145,
            "event_id": 80,
            "rule": 80,
            "level": 55,
            "firedtimes": 85,
            "description": 330,
        }
        for column in cleaned_columns:
            self.cleaned_tree.heading(column, text=cleaned_headings[column])
            self.cleaned_tree.column(
                column,
                width=cleaned_widths[column],
                anchor="w",
            )

        self.cleaned_scrollbar = ttk.Scrollbar(
            cleaned_table_frame,
            orient="vertical",
            command=self.cleaned_tree.yview,
        )
        cleaned_horizontal_scrollbar = ttk.Scrollbar(
            cleaned_table_frame,
            orient="horizontal",
            command=self.cleaned_tree.xview,
        )
        self.cleaned_tree.configure(
            yscrollcommand=self._on_cleaned_table_scroll,
            xscrollcommand=cleaned_horizontal_scrollbar.set,
        )
        cleaned_table_frame.rowconfigure(0, weight=1)
        cleaned_table_frame.columnconfigure(0, weight=1)
        self.cleaned_tree.grid(row=0, column=0, sticky="nsew")
        self.cleaned_scrollbar.grid(row=0, column=1, sticky="ns")
        cleaned_horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.cleaned_tree.bind("<Double-1>", self._on_cleaned_row_click)

        self._create_processed_data_table()

    def _create_processed_data_table(self):
        """Create the Agent/day dataset view used by the EDA calculations."""
        header = ttk.Frame(self.processed_data_tab)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(
            header,
            text="Dữ liệu tổng hợp theo Agent/ngày",
            style="Title.TLabel",
        ).pack(side="left")
        self.processed_data_state_var = tk.StringVar(value="Chưa có dữ liệu")
        ttk.Label(header, textvariable=self.processed_data_state_var).pack(side="right")

        ttk.Label(
            self.processed_data_tab,
            text=(
                "Mỗi dòng là một Agent trong một ngày; "
                "event_time hiển thị ngày tổng hợp."
            ),
        ).pack(anchor="w", pady=(0, 8))

        table_frame = ttk.Frame(self.processed_data_tab)
        table_frame.pack(fill="both", expand=True)
        columns = (
            "agent_name",
            "event_time",
            "total_events",
            "high_level_alerts",
            "unique_rules",
            "unique_event_ids",
            "unique_source_ips",
            "unique_users",
            "avg_rule_level",
            "max_rule_level",
        )
        self.processed_data_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
        )
        widths = {
            "agent_name": 145,
            "event_time": 115,
            "total_events": 105,
            "high_level_alerts": 130,
            "unique_rules": 105,
            "unique_event_ids": 125,
            "unique_source_ips": 135,
            "unique_users": 105,
            "avg_rule_level": 120,
            "max_rule_level": 120,
        }
        for column in columns:
            self.processed_data_tree.heading(column, text=column)
            self.processed_data_tree.column(
                column,
                width=widths[column],
                minwidth=80,
                anchor="center" if column != "agent_name" else "w",
            )

        vertical_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.processed_data_tree.yview,
        )
        horizontal_scrollbar = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.processed_data_tree.xview,
        )
        self.processed_data_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.processed_data_tree.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    def _create_status_bar(self):
        """Tạo thanh trạng thái cuối cửa sổ để báo tiến độ và kết quả thao tác."""
        self.status_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").pack(
            fill="x", side="bottom"
        )

    def _on_close(self):
        """Hủy lịch polling, đóng file CSV đang mở rồi giải phóng cửa sổ."""
        if self.processing_poll_after_id is not None:
            self.after_cancel(self.processing_poll_after_id)
            self.processing_poll_after_id = None
        if self.cleaned_csv_reader is not None:
            self.cleaned_csv_reader.close()
        self.destroy()

    def import_json(self):
        """Chọn raw JSON/CSV sạch và chạy đúng quy trình nhập tương ứng."""
        file_path = filedialog.askopenfilename(
            title="Chọn dữ liệu cảnh báo Wazuh",
            filetypes=[
                ("Dữ liệu Wazuh", "*.json *.csv"),
                ("JSON files", "*.json"),
                ("CSV files", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        if self.processing_thread and self.processing_thread.is_alive():
            messagebox.showwarning("Đang xử lý", "Vui lòng chờ dataset hiện tại hoàn tất.")
            return

        cleaned_path = self.project_root / "data" / "processed" / "wazuh_cleaned.csv"
        if cleaned_path.exists() and not messagebox.askyesno(
            "Xác nhận xử lý",
            "Kết quả CSV hiện tại sẽ được thay thế. Bạn có muốn tiếp tục?",
        ):
            return

        # Windows không cho phép thay CSV khi UI còn giữ file handle.
        if self.cleaned_csv_reader is not None:
            self.cleaned_csv_reader.close()
            self.cleaned_csv_reader = None

        self.import_button.configure(state="disabled")
        source_path = Path(file_path)
        is_cleaned_csv = source_path.suffix.lower() == ".csv"
        self.loading_var.set("Đang nạp CSV sạch..." if is_cleaned_csv else "Loading.....")
        self.quality_file_var.set(f"Dataset: {Path(file_path).name}")
        self.quality_state_var.set(
            "Đang kiểm tra CSV sạch..." if is_cleaned_csv else "Đang profiling..."
        )
        self.status_var.set(
            "Đang kiểm tra và nạp CSV sạch"
            if is_cleaned_csv
            else "Đang profiling dataset, giao diện vẫn có thể sử dụng"
        )
        self.notebook.select(self.data_quality_tab)

        self.processing_thread = threading.Thread(
            target=(
                self._process_cleaned_csv_worker
                if is_cleaned_csv
                else self._process_dataset_worker
            ),
            args=(source_path,),
            daemon=True,
        )
        self.processing_thread.start()
        self._schedule_processing_poll()

    def _process_dataset_worker(self, source_path):
        """Chạy profiling rồi cleaning raw JSON ở luồng nền."""
        try:
            profile_path = self.project_root / "reports" / "profiling_report.json"
            cleaned_path = self.project_root / "data" / "processed" / "wazuh_cleaned.csv"
            cleaning_path = self.project_root / "reports" / "cleaning_report.json"

            profile = DataProfilingService.profile(
                source_path,
                progress_callback=lambda rows: self.processing_queue.put(
                    ("progress", "Profiling", rows)
                ),
            )
            DataProfilingService.save_report(profile, profile_path)
            self.processing_queue.put(("stage", "Đang Validation/Cleaning..."))

            cleaning = DataCleaningService.clean_to_csv(
                source_path,
                cleaned_path,
                progress_callback=lambda rows: self.processing_queue.put(
                    ("progress", "Cleaning", rows)
                ),
            )
            DataCleaningService.save_report(cleaning, cleaning_path)
            self.processing_queue.put(("success", profile, cleaning))
        except Exception as error:
            self.processing_queue.put(("error", str(error)))

    def _process_cleaned_csv_worker(self, source_path):
        """Kiểm tra schema CSV sạch rồi đưa vào dataset làm việc."""
        """Validate and activate an existing cleaned CSV without JSON cleaning."""
        try:
            frame = EdaService.load_dataset(source_path)
            quality = self._cleaned_csv_quality(frame)
            cleaned_path = self.project_root / "data" / "processed" / "wazuh_cleaned.csv"
            cleaned_path.parent.mkdir(parents=True, exist_ok=True)
            source_columns = pd.read_csv(source_path, nrows=0).columns
            legacy_risk_columns = [
                column
                for column in (
                    "agent_risk_index",
                    "alert_risk_level",
                    "agent_risk_level",
                )
                if column in source_columns
            ]
            if legacy_risk_columns:
                # Migrate older cleaned CSV files without keeping generated Risk fields.
                source_data = pd.read_csv(source_path, low_memory=False)
                source_data = source_data.drop(columns=legacy_risk_columns)
                temporary_path = cleaned_path.with_suffix(".csv.tmp")
                source_data.to_csv(temporary_path, index=False, encoding="utf-8")
                temporary_path.replace(cleaned_path)
            elif source_path.resolve() != cleaned_path.resolve():
                shutil.copyfile(source_path, cleaned_path)
            self.processing_queue.put(("csv_success", quality, source_path.name))
        except Exception as error:
            self.processing_queue.put(("error", str(error)))

    def _schedule_processing_poll(self):
        """Lên lịch kiểm tra queue của worker sau 200 ms mà không khóa Tkinter."""
        if self.processing_poll_after_id is None:
            self.processing_poll_after_id = self.after(200, self._poll_processing_queue)

    def _poll_processing_queue(self):
        """Đưa kết quả worker về main thread để cập nhật widget an toàn."""
        self.processing_poll_after_id = None
        finished = False

        while True:
            try:
                message = self.processing_queue.get_nowait()
            except queue.Empty:
                break

            message_type = message[0]
            if message_type == "progress":
                _kind, stage, rows = message
                self.quality_state_var.set(f"{stage}: {self._format_number(rows)} dòng")
                self.status_var.set(
                    f"{stage}: đã xử lý {self._format_number(rows)} dòng"
                )
            elif message_type == "stage":
                self.quality_state_var.set(message[1])
            elif message_type == "success":
                _kind, profile, cleaning = message
                self._update_quality_view(profile, cleaning)
                self._reset_cleaned_log_reader()
                self._reload_processed_data_view()
                self.eda_panel.reload_dataset()
                self.model_panel.reload_dataset()
                self.external_validation_panel.clear_results()
                self.loading_var.set("")
                self.import_button.configure(state="normal")
                self.processing_thread = None
                self.quality_state_var.set("Hoàn thành")
                self.status_var.set("Đã tạo dataset sạch và báo cáo Before/After")
                messagebox.showinfo(
                    "Xử lý hoàn tất",
                    f"Đầu vào: {self._format_number(profile['input']['total_rows'])}\n"
                    f"Đã loại: {self._format_number(cleaning['actions']['removed_unique_rows'])}\n"
                    f"Dữ liệu sạch: {self._format_number(cleaning['after']['output_rows'])}",
                )
                finished = True
            elif message_type == "csv_success":
                _kind, quality, source_name = message
                row_count = quality["row_count"]
                self.cleaned_total_rows = row_count
                self._update_cleaned_csv_quality_view(quality, source_name)
                self._reset_cleaned_log_reader()
                self._reload_processed_data_view()
                self.eda_panel.reload_dataset()
                self.model_panel.reload_dataset()
                self.external_validation_panel.clear_results()
                self.loading_var.set("")
                self.import_button.configure(state="normal")
                self.processing_thread = None
                self.quality_file_var.set(f"Dataset CSV: {source_name}")
                self.quality_state_var.set("Đã nạp CSV sạch")
                self.status_var.set("Đã kiểm tra và nạp CSV sạch vào phân tích")
                messagebox.showinfo(
                    "Nạp CSV hoàn tất",
                    f"Dữ liệu sạch: {self._format_number(row_count)} dòng",
                )
                finished = True
            elif message_type == "error":
                self.loading_var.set("")
                self.import_button.configure(state="normal")
                self.processing_thread = None
                self.quality_state_var.set("Xử lý thất bại")
                self.status_var.set("Không xử lý được dataset")
                self._reset_cleaned_log_reader()
                messagebox.showerror("Lỗi xử lý dữ liệu", message[1])
                finished = True

        if not finished and self.processing_thread is not None:
            self._schedule_processing_poll()

    def _load_existing_quality_reports(self):
        """Nạp báo cáo profiling/cleaning gần nhất nếu còn khớp CSV hiện tại.

        Nếu số dòng trong báo cáo cũ không khớp CSV, hàm bỏ số liệu cũ và tính
        mô tả chất lượng trực tiếp từ CSV đang được ứng dụng sử dụng.
        """
        profile_path = self.project_root / "reports" / "profiling_report.json"
        cleaning_path = self.project_root / "reports" / "cleaning_report.json"
        if not profile_path.exists() or not cleaning_path.exists():
            return
        try:
            profile = json.loads(profile_path.read_text(encoding="utf-8"))
            cleaning = json.loads(cleaning_path.read_text(encoding="utf-8"))
            cleaned_path = (
                self.project_root / "data" / "processed" / "wazuh_cleaned.csv"
            )
            if cleaned_path.exists():
                frame = EdaService.load_dataset(cleaned_path)
                if len(frame) != cleaning["after"]["output_rows"]:
                    quality = self._cleaned_csv_quality(frame)
                    self._update_cleaned_csv_quality_view(
                        quality,
                        cleaned_path.name,
                    )
                    self.cleaned_total_rows = quality["row_count"]
                    self.quality_state_var.set("Đã tải CSV sạch hiện tại")
                    return
            self._update_quality_view(profile, cleaning)
            self.quality_state_var.set("Đã tải kết quả gần nhất")
        except (OSError, json.JSONDecodeError, KeyError):
            self.quality_state_var.set("Không đọc được báo cáo gần nhất")

    @staticmethod
    def _cleaned_csv_quality(frame):
        """Summarize the CSV currently used by the analysis screens."""
        derived_columns = {
            "analysis_source_ip",
            "analysis_user",
            "event_date",
            # Legacy generated columns are ignored and no longer displayed.
            "agent_risk_index",
            "alert_risk_level",
            "agent_risk_level",
        }
        source_columns = [
            column for column in frame.columns if column not in derived_columns
        ]
        row_count = len(frame)
        missing_fields = []
        for column in source_columns:
            missing_count = int(frame[column].isna().sum())
            missing_fields.append(
                {
                    "field": column,
                    "missing": missing_count,
                    "percent": (
                        missing_count / row_count * 100 if row_count else 0.0
                    ),
                }
            )
        return {
            "row_count": row_count,
            # The cleaned CSV no longer carries Wazuh alert.id.  event_id is
            # the Windows event type and may legitimately repeat, so it must
            # not be used as the duplicate-cleaning key.
            "duplicate_rows": 0,
            "missing_fields": missing_fields,
        }

    def _update_cleaned_csv_quality_view(self, quality, source_name):
        """Replace stale JSON-cleaning metrics with the imported CSV metrics."""
        row_count = quality["row_count"]
        values = {
            "input": self._format_number(row_count),
            "duplicates": self._format_number(quality["duplicate_rows"]),
            "output": self._format_number(row_count),
            "retention": "100%",
        }
        for key, value in values.items():
            self.quality_card_values[key].configure(text=value)

        self.quality_file_var.set(f"Dataset CSV: {source_name}")

        for item in self.removed_tree.get_children():
            self.removed_tree.delete(item)
        self.removed_tree.insert(
            "",
            "end",
            values=("Không cleaning lại CSV sạch", "0"),
        )

        for item in self.missing_tree.get_children():
            self.missing_tree.delete(item)
        for field in quality["missing_fields"]:
            self.missing_tree.insert(
                "",
                "end",
                values=(
                    field["field"],
                    self._format_number(field["missing"]),
                    f"{field['percent']:.4f}%".replace(".", ","),
                ),
            )

    def _update_quality_view(self, profile, cleaning):
        """Đưa báo cáo raw profiling và cleaning lên card/bảng Before–After."""
        input_rows = profile["input"]["total_rows"]
        duplicate_rows = profile["quality"]["duplicate_id_rows"]
        output_rows = cleaning["after"]["output_rows"]
        self.cleaned_total_rows = output_rows
        retention = cleaning["after"]["retention_percent"]
        values = {
            "input": self._format_number(input_rows),
            "duplicates": self._format_number(duplicate_rows),
            "output": self._format_number(output_rows),
            "retention": f"{retention:.4f}%".replace(".", ","),
        }
        for key, value in values.items():
            self.quality_card_values[key].configure(text=value)

        self.quality_file_var.set(f"Dataset: {profile['metadata']['input_file']}")

        for item in self.removed_tree.get_children():
            self.removed_tree.delete(item)
        reason_names = {
            "duplicate_alert_id": "Trùng alert.id",
            "missing_id": "Thiếu alert.id",
            "missing_timestamp": "Thiếu timestamp",
            "missing_agent_id": "Thiếu agent.id",
            "missing_rule_id": "Thiếu rule.id",
            "missing_rule_level": "Thiếu rule.level",
            "invalid_timestamp": "Timestamp không hợp lệ",
            "invalid_rule_level": "Rule level không hợp lệ",
            "manager_agent_000": "Agent 000",
        }
        removed = cleaning["actions"].get("removed_by_reason", {})
        for reason, count in removed.items():
            self.removed_tree.insert(
                "",
                "end",
                values=(reason_names.get(reason, reason), self._format_number(count)),
            )

        for item in self.missing_tree.get_children():
            self.missing_tree.delete(item)
        fields = profile.get("fields", {})
        sorted_fields = sorted(
            fields.items(),
            key=lambda item: item[1].get("missing", 0),
            reverse=True,
        )
        for field, details in sorted_fields:
            self.missing_tree.insert(
                "",
                "end",
                values=(
                    field,
                    self._format_number(details.get("missing", 0)),
                    f"{details.get('missing_percent', 0):.4f}%".replace(".", ","),
                ),
            )

    def _reload_processed_data_view(self):
        """Load and show the same Agent/day dataset used throughout EDA."""
        for item in self.processed_data_tree.get_children():
            self.processed_data_tree.delete(item)

        csv_path = self.project_root / "data" / "processed" / "wazuh_cleaned.csv"
        if not csv_path.exists():
            self.processed_data_state_var.set("Chưa có CSV sạch để tổng hợp")
            return

        try:
            frame = EdaService.load_dataset(csv_path)
            summary = EdaService.aggregate_agent_day(frame)
        except (OSError, ValueError, KeyError) as error:
            self.processed_data_state_var.set(f"Không tổng hợp được dữ liệu: {error}")
            return

        for row in summary.itertuples(index=False):
            event_time = row.event_date.strftime("%Y-%m-%d")
            values = (
                row.agent_name,
                event_time,
                str(int(row.total_events)),
                str(int(row.high_level_alerts)),
                str(int(row.unique_rules)),
                str(int(row.unique_event_ids)),
                str(int(row.unique_source_ips)),
                str(int(row.unique_users)),
                "-" if pd.isna(row.avg_rule_level) else f"{row.avg_rule_level:.2f}",
                "-" if pd.isna(row.max_rule_level) else str(int(row.max_rule_level)),
            )
            self.processed_data_tree.insert("", "end", values=values)

        self.processed_data_state_var.set(
            f"Đã tổng hợp {self._format_number(len(summary))} dòng Agent/ngày"
        )

    def _reset_cleaned_log_reader(self):
        """Đóng reader cũ, xóa bảng log và mở lại CSV sạch từ dòng đầu tiên."""
        if self.cleaned_csv_reader is not None:
            self.cleaned_csv_reader.close()
        self.cleaned_csv_reader = None
        self.cleaned_rows.clear()
        self.cleaned_row_counter = 0
        self.cleaned_load_scheduled = False
        for item in self.cleaned_tree.get_children():
            self.cleaned_tree.delete(item)

        csv_path = self.project_root / "data" / "processed" / "wazuh_cleaned.csv"
        if not csv_path.exists():
            self.cleaned_list_state_var.set("Chưa có CSV sạch")
            return
        try:
            self.cleaned_csv_reader = CleanedCsvReader(csv_path, batch_size=20)
            self._load_next_cleaned_batch()
        except (OSError, ValueError) as error:
            self.cleaned_list_state_var.set(f"Không đọc được CSV: {error}")

    def _load_next_cleaned_batch(self):
        """Nạp thêm một batch CSV thay vì đổ toàn bộ vào Treeview."""
        self.cleaned_load_scheduled = False
        if self.cleaned_csv_reader is None or self.cleaned_csv_reader.end_of_file:
            return

        rows = self.cleaned_csv_reader.read_next_batch()
        for row in rows:
            for legacy_column in (
                "agent_risk_index",
                "alert_risk_level",
                "agent_risk_level",
            ):
                row.pop(legacy_column, None)
            self.cleaned_row_counter += 1
            item_id = f"cleaned-{self.cleaned_row_counter}"
            self.cleaned_rows[item_id] = row
            self.cleaned_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    row.get("timestamp_utc", ""),
                    row.get("agent_name", ""),
                    row.get("source_ip", "") or row.get("src_ip", ""),
                    row.get("target_user_name", "") or row.get("dst_user", ""),
                    row.get("event_id", ""),
                    row.get("rule_id", ""),
                    row.get("rule_level", ""),
                    row.get("rule_firedtimes", ""),
                    row.get("rule_description", ""),
                ),
            )

        total_text = (
            self._format_number(self.cleaned_total_rows)
            if self.cleaned_total_rows
            else "?"
        )
        suffix = " - đã hết dữ liệu" if self.cleaned_csv_reader.end_of_file else ""
        self.cleaned_list_state_var.set(
            f"Đã tải {self._format_number(self.cleaned_row_counter)} / "
            f"{total_text} dòng{suffix}"
        )

    def _on_cleaned_table_scroll(self, first, last):
        """Nạp batch tiếp theo khi thanh cuộn đến gần cuối bảng log."""
        self.cleaned_scrollbar.set(first, last)
        if (
            float(last) >= 0.98
            and self.cleaned_csv_reader is not None
            and not self.cleaned_csv_reader.end_of_file
            and not self.cleaned_load_scheduled
        ):
            self.cleaned_load_scheduled = True
            self.after_idle(self._load_next_cleaned_batch)

    def _on_cleaned_row_click(self, event):
        """Mở cửa sổ JSON chi tiết của dòng log được người dùng nhấp chọn."""
        if self.cleaned_tree.identify_region(event.x, event.y) != "cell":
            return
        item_id = self.cleaned_tree.identify_row(event.y)
        row = self.cleaned_rows.get(item_id)
        if row is None:
            return

        window = tk.Toplevel(self)
        window.title(f"Chi tiết log - Rule {row.get('rule_id', '')}")
        window.geometry("760x600")
        text = tk.Text(window, wrap="word", padx=12, pady=12)
        text.pack(fill="both", expand=True)
        text.insert("end", json.dumps(row, ensure_ascii=False, indent=2))
        text.configure(state="disabled")

    @staticmethod
    def _format_number(value):
        """Định dạng số nguyên theo nhóm hàng nghìn bằng dấu chấm trên UI."""
        return f"{int(value):,}".replace(",", ".")

    def refresh_data_views(self):
        """Reload the cleaned dataset in every remaining application view."""
        self._reset_cleaned_log_reader()
        self._reload_processed_data_view()
        self.eda_panel.reload_dataset()
        self.model_panel.reload_dataset()
        self.external_validation_panel.clear_results()
        self.status_var.set("Đang làm mới dữ liệu phân tích...")
