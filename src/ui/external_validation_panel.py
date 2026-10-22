"""Kiểm thử bộ dữ liệu độc lập mà không huấn luyện lại mô hình cũ.

KỸ THUẬT: external holdout validation; làm sạch file mới rồi chỉ predict.
VẤN ĐỀ: cần biết công thức học từ dữ liệu cũ hoạt động ra sao trên dữ liệu khác.
TÁC DỤNG: MSE/R² phản ánh khả năng tổng quát hóa ngoài tập huấn luyện.
"""

import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.services.data_cleaning_service import DataCleaningService
from src.services.eda_service import EdaService
from src.services.model_service import ModelService


class ExternalValidationPanel(ttk.Frame):
    """Test fitted HQTT/HQDT Pipelines on a separate JSON or clean CSV."""

    def __init__(self, parent, model_panel):
        """Nhận Pipeline từ ModelPanel và khởi tạo trạng thái kiểm thử."""
        super().__init__(parent, padding=10)
        self.model_panel = model_panel
        self.load_queue = queue.Queue()
        self.load_thread = None
        self.poll_after_id = None
        self.external_summary = pd.DataFrame()
        self.linear_evaluation = None
        self.polynomial_evaluation = None
        self.degree_evaluations = {}
        self._create_ui()

    def _create_ui(self):
        """Tạo nút nạp file, bảng chỉ số, bảng dự đoán và vùng biểu đồ."""
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 8))
        ttk.Label(
            toolbar,
            text="Kiểm thử mô hình bằng bộ dữ liệu độc lập",
            style="Title.TLabel",
        ).pack(side="left")
        self.load_button = ttk.Button(
            toolbar,
            text="Nạp bộ dữ liệu kiểm thử",
            command=self.load_external_dataset,
        )
        self.load_button.pack(side="right")

        self.status_var = tk.StringVar(
            value=(
                "Chưa nạp dữ liệu kiểm thử. Dữ liệu mới chỉ được "
                "predict(), không fit() lại mô hình."
            )
        )
        ttk.Label(self, textvariable=self.status_var).pack(
            anchor="w", pady=(0, 8)
        )

        comparison_frame = ttk.LabelFrame(
            self,
            text="Bằng chứng đánh giá và đối chiếu",
            padding=6,
        )
        comparison_frame.pack(fill="both", expand=False)
        metric_columns = (
            "model",
            "scope",
            "samples",
            "mse",
            "r_squared",
        )
        self.metric_tree = ttk.Treeview(
            comparison_frame,
            columns=metric_columns,
            show="headings",
            height=3,
        )
        metric_headings = {
            "model": "Mô hình",
            "scope": "Phạm vi đánh giá",
            "samples": "Số mẫu",
            "mse": "MSE",
            "r_squared": "R²",
        }
        for column in metric_columns:
            self.metric_tree.heading(column, text=metric_headings[column])
            self.metric_tree.column(
                column,
                width=230 if column == "scope" else 135,
                anchor="center",
            )
        self._add_scrollbars(comparison_frame, self.metric_tree)

        content = ttk.Panedwindow(self, orient="horizontal")
        content.pack(fill="both", expand=True, pady=(8, 0))
        data_frame = ttk.LabelFrame(
            content,
            text="Kết quả dự đoán trên từng Agent/ngày",
            padding=6,
        )
        plot_frame = ttk.LabelFrame(
            content,
            text="Trực quan đánh giá trên bộ dữ liệu mới",
            padding=6,
        )
        content.add(data_frame, weight=3)
        content.add(plot_frame, weight=2)

        detail_columns = (
            "agent_name",
            "event_date",
            "actual",
            "linear_predicted",
            "polynomial_degree_2_predicted",
            "polynomial_predicted",
        )
        self.detail_tree = ttk.Treeview(
            data_frame,
            columns=detail_columns,
            show="headings",
        )
        detail_headings = {
            "agent_name": "agent_name",
            "event_date": "event_date",
            "actual": "total_events thực tế",
            "linear_predicted": "total_events_HQTT",
            "polynomial_degree_2_predicted": "total_events_HQĐT_bậc_2",
            "polynomial_predicted": "total_events_HQĐT_chính",
        }
        for column in detail_columns:
            self.detail_tree.heading(column, text=detail_headings[column])
            self.detail_tree.column(column, width=155, anchor="center")
        self._add_scrollbars(data_frame, self.detail_tree)

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.linear_axis = self.figure.add_subplot(211)
        self.polynomial_axis = self.figure.add_subplot(212)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self._clear_plots()

    @staticmethod
    def _add_scrollbars(parent, tree):
        """Gắn thanh cuộn ngang/dọc cho một Treeview."""
        vertical = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

    def load_external_dataset(self):
        """Chọn JSON/CSV mới và xử lý nền để giao diện không bị treo."""
        if self.load_thread and self.load_thread.is_alive():
            messagebox.showwarning(
                "Đang xử lý",
                "Vui lòng chờ bộ dữ liệu kiểm thử hiện tại.",
            )
            return
        if (
            self.model_panel.model_result is None
            or self.model_panel.polynomial_result is None
        ):
            messagebox.showwarning(
                "Chưa có mô hình",
                "Hãy huấn luyện HQTT và HQĐT trước khi kiểm thử.",
            )
            return
        polynomial_candidates = getattr(
            self.model_panel,
            "polynomial_candidate_results",
            {},
        )
        if 2 not in polynomial_candidates:
            messagebox.showwarning(
                "Chưa có Pipeline tham khảo",
                "Hãy bấm Huấn luyện lại để tạo các Pipeline HQĐT bậc 1–10 "
                "từ dữ liệu cũ trước khi nạp bộ kiểm thử.",
            )
            return

        file_path = filedialog.askopenfilename(
            title="Chọn bộ dữ liệu kiểm thử độc lập",
            filetypes=[
                ("Dữ liệu Wazuh", "*.json *.csv"),
                ("JSON files", "*.json"),
                ("CSV sạch", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.load_button.configure(state="disabled")
        self.status_var.set(
            f"Đang xử lý bộ kiểm thử: {Path(file_path).name}..."
        )
        linear_model = self.model_panel.model_result
        polynomial_model = self.model_panel.polynomial_result
        degree = self.model_panel.polynomial_degree
        self.load_thread = threading.Thread(
            target=self._load_worker,
            args=(
                Path(file_path),
                linear_model,
                polynomial_model,
                polynomial_candidates,
                degree,
            ),
            daemon=True,
        )
        self.load_thread.start()
        self._schedule_poll()

    def _load_worker(
        self,
        source_path,
        linear_model,
        polynomial_model,
        polynomial_candidates,
        degree,
    ):
        """Làm sạch/tổng hợp file mới rồi predict bằng các Pipeline cũ."""
        try:
            if source_path.suffix.lower() == ".csv":
                dataset = EdaService.load_dataset(source_path)
            else:
                with tempfile.TemporaryDirectory() as temporary_directory:
                    cleaned_path = Path(temporary_directory) / "external_cleaned.csv"
                    DataCleaningService.clean_to_csv(source_path, cleaned_path)
                    dataset = EdaService.load_dataset(cleaned_path)
            summary = EdaService.aggregate_agent_day(dataset).reset_index(drop=True)
            # QUAN TRỌNG: evaluate_external chỉ predict, không fit dữ liệu mới.
            linear_evaluation = ModelService.evaluate_external(
                summary,
                linear_model,
            )
            polynomial_evaluation = ModelService.evaluate_external(
                summary,
                polynomial_model,
            )
            # So sánh bậc chỉ để tham khảo trên bộ mới; không đổi công thức chính.
            degree_evaluations = {
                candidate_degree: ModelService.evaluate_external(
                    summary,
                    candidate_result,
                )
                for candidate_degree, candidate_result
                in polynomial_candidates.items()
            }
            self.load_queue.put(
                (
                    "success",
                    source_path.name,
                    summary,
                    linear_evaluation,
                    polynomial_evaluation,
                    degree_evaluations,
                    degree,
                )
            )
        except Exception as error:
            self.load_queue.put(("error", str(error)))

    def _schedule_poll(self):
        """Lên lịch đọc queue kết quả worker mà không khóa UI."""
        if self.poll_after_id is None:
            self.poll_after_id = self.after(200, self._poll_queue)

    def _poll_queue(self):
        """Nhận kết quả worker trên main thread an toàn của Tkinter."""
        self.poll_after_id = None
        try:
            message = self.load_queue.get_nowait()
        except queue.Empty:
            # Keep polling until the worker's success/error message is read.
            # Checking is_alive() here creates a race: the worker can enqueue
            # its result and finish between get_nowait() and is_alive(), which
            # leaves the UI permanently showing "Đang xử lý".
            if self.load_thread is not None:
                self._schedule_poll()
            return

        self.load_button.configure(state="normal")
        self.load_thread = None
        if message[0] == "error":
            self.status_var.set(f"Không kiểm thử được: {message[1]}")
            messagebox.showerror("Lỗi kiểm thử", message[1])
            return

        (
            _kind,
            source_name,
            self.external_summary,
            self.linear_evaluation,
            self.polynomial_evaluation,
            self.degree_evaluations,
            degree,
        ) = message
        try:
            self._show_metrics(degree)
            self._show_details()
            self._draw_plots(degree)
        except Exception as error:
            self.status_var.set(f"Không hiển thị được kết quả: {error}")
            messagebox.showerror("Lỗi hiển thị kết quả", str(error))
            return
        self.status_var.set(
            f"Đã dự đoán {self.linear_evaluation['sample_count']} dòng có log "
            f"từ {source_name} bằng mô hình cũ; không huấn luyện lại."
        )

    def _show_metrics(self, degree):
        """Hiển thị MSE/R² của công thức cũ trên 100% dữ liệu mới có log."""
        self._clear_tree(self.metric_tree)
        external_rows = (
            ("HQTT", self.linear_evaluation),
            (f"HQĐT bậc {degree}", self.polynomial_evaluation),
        )
        for model_name, evaluation in external_rows:
            row = (
                model_name,
                "100% bộ dữ liệu kiểm thử độc lập",
                evaluation["sample_count"],
                evaluation["mse"],
                evaluation["r_squared"],
            )
            self.metric_tree.insert(
                "",
                "end",
                values=self._format_metric_row(row),
                tags=("external",),
            )
        self.metric_tree.tag_configure("external", background="#DDEBF7")

    def _show_details(self):
        """Hiển thị từng dòng thực tế và dự đoán của các mô hình cũ."""
        self._clear_tree(self.detail_tree)
        self.detail_tree.heading(
            "polynomial_predicted",
            text=f"total_events_HQĐT_bậc_{self.model_panel.polynomial_degree}",
        )
        linear = self.linear_evaluation["comparison"].reset_index(drop=True)
        polynomial_degree_2 = self.degree_evaluations[2][
            "comparison"
        ].reset_index(drop=True)
        polynomial = self.polynomial_evaluation["comparison"].reset_index(drop=True)
        for index, row in linear.iterrows():
            self.detail_tree.insert(
                "",
                "end",
                values=(
                    row.get("agent_name", "-"),
                    self._format_date(row.get("event_date")),
                    self._format_decimal(row["actual"], 0),
                    self._format_decimal(row["predicted"], 2),
                    self._format_decimal(
                        polynomial_degree_2.loc[index, "predicted"], 2
                    ),
                    self._format_decimal(
                        polynomial.loc[index, "predicted"], 2
                    ),
                ),
            )

    def _draw_plots(self, degree):
        """Vẽ phân phối dự đoán và MSE ngoài mẫu theo bậc tham khảo."""
        self.linear_axis.clear()
        comparison = self.linear_evaluation["comparison"]
        sns.kdeplot(
            data=comparison,
            x="actual",
            ax=self.linear_axis,
            color="#D62728",
            linewidth=2,
            label="Thực tế",
            warn_singular=False,
        )
        sns.kdeplot(
            data=comparison,
            x="predicted",
            ax=self.linear_axis,
            color="#1F77B4",
            linewidth=2,
            label="Dự đoán HQTT",
            warn_singular=False,
        )
        self.linear_axis.set_title("Distribution Plot - HQTT")
        self.linear_axis.set_xlabel("total_events")
        self.linear_axis.set_ylabel("Mật độ")
        self.linear_axis.grid(alpha=0.25)
        self.linear_axis.legend(fontsize=8)

        self.polynomial_axis.clear()
        degrees = sorted(self.degree_evaluations)
        train_mse = [
            self.model_panel.polynomial_candidate_results[item].mse
            for item in degrees
        ]
        external_mse = [
            self.degree_evaluations[item]["mse"] for item in degrees
        ]
        self.polynomial_axis.plot(
            degrees,
            train_mse,
            marker="o",
            label="MSE Train cũ",
        )
        self.polynomial_axis.plot(
            degrees,
            external_mse,
            marker="o",
            label="MSE dữ liệu mới",
        )
        self.polynomial_axis.axvline(
            degree,
            color="#00A651",
            linestyle="--",
            label=f"Công thức đang dùng: bậc {degree}",
        )
        finite_external = [
            (item, mse)
            for item, mse in zip(degrees, external_mse)
            if item >= 2 and np.isfinite(mse)
        ]
        if finite_external:
            best_degree, best_mse = min(finite_external, key=lambda row: row[1])
            self.polynomial_axis.scatter(
                [best_degree],
                [best_mse],
                color="#7B1FA2",
                s=55,
                zorder=5,
                label=f"HQĐT tham khảo tốt nhất: bậc {best_degree}",
            )
        positive_values = [
            value
            for value in train_mse + external_mse
            if np.isfinite(value) and value > 0
        ]
        if len(positive_values) == len(train_mse) + len(external_mse):
            self.polynomial_axis.set_yscale("log")
        self.polynomial_axis.set_xticks(degrees)
        self.polynomial_axis.set_title(
            "MSE theo bậc trên dữ liệu mới (chỉ tham khảo)"
        )
        self.polynomial_axis.set_xlabel("Bậc đa thức")
        self.polynomial_axis.set_ylabel("MSE (thang log)")
        self.polynomial_axis.grid(alpha=0.25)
        self.polynomial_axis.legend(fontsize=8)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    def clear_results(self):
        """Invalidate external evidence after the training dataset changes."""
        self.external_summary = pd.DataFrame()
        self.linear_evaluation = None
        self.polynomial_evaluation = None
        self.degree_evaluations = {}
        self._clear_tree(self.metric_tree)
        self._clear_tree(self.detail_tree)
        self._clear_plots()
        self.status_var.set(
            "Mô hình huấn luyện đã thay đổi; hãy nạp lại bộ dữ liệu kiểm thử."
        )

    def _clear_plots(self):
        """Xóa nội dung biểu đồ khi chưa có hoặc khi đổi bộ kiểm thử."""
        for axis, title in (
            (self.linear_axis, "HQTT"),
            (self.polynomial_axis, "MSE HQĐT theo bậc"),
        ):
            axis.clear()
            axis.set_title(title)
            axis.text(
                0.5,
                0.5,
                "Chưa có dữ liệu kiểm thử",
                ha="center",
                va="center",
                transform=axis.transAxes,
            )
        self.figure.tight_layout()
        self.canvas.draw_idle()

    @staticmethod
    def _clear_tree(tree):
        """Xóa toàn bộ dòng đang có trong một Treeview."""
        for item in tree.get_children():
            tree.delete(item)

    @classmethod
    def _format_metric_row(cls, row):
        """Định dạng một hàng MSE/R² trước khi đưa lên bảng."""
        return tuple(
            value
            if value == "-" or index < 3
            else cls._format_decimal(value, 6 if index == 4 else 4)
            for index, value in enumerate(row)
        )

    @staticmethod
    def _format_date(value):
        """Định dạng ngày theo YYYY-MM-DD cho bảng kết quả."""
        if pd.isna(value):
            return "-"
        return pd.Timestamp(value).strftime("%Y-%m-%d")

    @staticmethod
    def _format_decimal(value, digits):
        """Định dạng số theo số chữ số và dấu phẩy thập phân."""
        formatted = f"{float(value):,.{digits}f}"
        return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
