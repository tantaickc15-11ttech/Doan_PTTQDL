"""Giao diện xây dựng, dự đoán và so sánh mô hình hồi quy.

KỸ THUẬT: phối hợp Pipeline và trình bày bằng bảng, Distribution Plot, MSE.
VẤN ĐỀ: cần thấy rõ dữ liệu huấn luyện, dự đoán và ba cách đánh giá.
TÁC DỤNG: lớp này điều phối/hiển thị; phép học nằm trong ModelService.
"""

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from src.services.eda_service import EdaService
from src.services.model_service import ModelService


class ModelPanel(ttk.Frame):
    """Show training data, learned formula, predictions and visual evaluation."""

    def __init__(self, parent, csv_path: Path):
        """Khởi tạo trạng thái hai mô hình, tạo UI rồi nạp dataset hiện có."""
        super().__init__(parent, padding=8)
        self.csv_path = Path(csv_path)
        self.summary = pd.DataFrame()
        self.model_result = None
        self.polynomial_result = None
        self.polynomial_candidate_results = {}
        self.polynomial_degree = None
        self.degree_selection_result = None
        self.train_test_result = None
        self.polynomial_train_test_result = None
        self.cross_validation_result = None
        self.polynomial_cross_validation_result = None
        self.input_vars = {}
        self.polynomial_input_vars = {}
        self._create_header()
        self._create_content()
        self.reload_dataset()

    def _create_header(self):
        """Tạo tiêu đề, mô tả target/biến và nút huấn luyện lại."""
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(
            header,
            text="Xây dựng và so sánh mô hình hồi quy",
            style="Title.TLabel",
        ).pack(side="left")
        ttk.Button(
            header,
            text="Huấn luyện lại",
            command=self.train_model,
        ).pack(side="right")

        self.status_var = tk.StringVar(value="Đang đọc dữ liệu...")
        ttk.Label(self, textvariable=self.status_var).pack(anchor="w", pady=(0, 6))
        ttk.Label(
            self,
            text=(
                "Target: total_events | Biến số: 7 biến được chọn bằng Pearson | "
                "Biến phân loại: agent_name được chọn bằng ANOVA | "
                "Mô hình: HQTT đa biến và HQĐT tự chọn bậc"
            ),
        ).pack(anchor="w", pady=(0, 8))

    def _create_content(self):
        """Tạo notebook dữ liệu–huấn luyện và đánh giá mô hình."""
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.training_tab = ttk.Frame(notebook, padding=6)
        self.evaluation_tab = ttk.Frame(notebook, padding=6)
        notebook.add(self.training_tab, text="Dữ liệu & huấn luyện")
        notebook.add(self.evaluation_tab, text="Đánh giá Model dự đoán")
        self._create_training_tab()
        self._create_evaluation_tab()

    @staticmethod
    def _add_scrollbars(parent, tree):
        """Gắn thanh cuộn ngang/dọc cho bảng Treeview."""
        vertical = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")

    def _create_training_tab(self):
        """Tạo bảng Agent/ngày và vùng nhập dự đoán của hai mô hình."""
        panes = ttk.Panedwindow(self.training_tab, orient="horizontal")
        panes.pack(fill="both", expand=True)
        training = ttk.Frame(panes)
        prediction = ttk.Frame(panes)
        panes.add(training, weight=3)
        panes.add(prediction, weight=2)

        frame = ttk.LabelFrame(
            training,
            text="Dữ liệu thực tế dùng để xây dựng mô hình",
            padding=6,
        )
        frame.pack(fill="both", expand=True)
        columns = (
            "agent_name",
            "event_date",
            *ModelService.NUMERIC_FEATURES,
            ModelService.TARGET,
            "predicted_total_events_linear",
            "predicted_total_events_polynomial",
        )
        self.training_tree = ttk.Treeview(frame, columns=columns, show="headings")
        for column in columns:
            prediction_headings = {
                "predicted_total_events_linear": "total_events_HQTT",
                "predicted_total_events_polynomial": "total_events_HQĐT",
            }
            heading = prediction_headings.get(column, column)
            self.training_tree.heading(column, text=heading)
            self.training_tree.column(
                column,
                width=135 if column in ("agent_name", "event_date") else 120,
                minwidth=90,
                anchor="center",
            )
        self._add_scrollbars(frame, self.training_tree)
        self._create_prediction_panel(prediction)

    def _create_prediction_panel(self, prediction):
        """Tạo hai form HQTT/HQĐT xếp dọc trong vùng dự đoán."""
        forms = ttk.Panedwindow(prediction, orient="vertical")
        forms.pack(fill="both", expand=True, padx=(8, 0))
        linear_parent = ttk.Frame(forms)
        polynomial_parent = ttk.Frame(forms)
        forms.add(linear_parent, weight=1)
        forms.add(polynomial_parent, weight=1)

        self.prediction_var = tk.StringVar(value="Tổng Event HQTT: -")
        self.polynomial_prediction_var = tk.StringVar(
            value="Tổng Event HQĐT: -"
        )
        self.agent_input = self._create_prediction_form(
            linear_parent,
            "Hồi quy tuyến tính đa biến",
            self.input_vars,
            self.prediction_var,
            self.predict_one,
        )
        self.polynomial_agent_input = self._create_prediction_form(
            polynomial_parent,
            "Hồi quy đa thức",
            self.polynomial_input_vars,
            self.polynomial_prediction_var,
            self.predict_polynomial,
        )

    def _create_prediction_form(
        self,
        parent,
        title,
        input_vars,
        result_var,
        predict_command,
    ):
        """Tạo các ô nhập, nút lấy dòng và nút dự đoán cho một mô hình."""
        input_frame = ttk.LabelFrame(
            parent,
            text=title,
            padding=8,
        )
        input_frame.pack(fill="both", expand=True, padx=3)
        input_vars["agent_name"] = tk.StringVar()
        ttk.Label(input_frame, text="agent_name").grid(
            row=0, column=0, sticky="w", padx=3, pady=3
        )
        agent_input = ttk.Combobox(
            input_frame,
            textvariable=input_vars["agent_name"],
            state="readonly",
            width=21,
        )
        agent_input.grid(row=0, column=1, sticky="ew", padx=3, pady=3)

        for row_index, feature in enumerate(ModelService.NUMERIC_FEATURES, start=1):
            input_vars[feature] = tk.StringVar(value="0")
            ttk.Label(input_frame, text=feature).grid(
                row=row_index, column=0, sticky="w", padx=3, pady=3
            )
            ttk.Entry(
                input_frame,
                textvariable=input_vars[feature],
                width=24,
            ).grid(row=row_index, column=1, sticky="ew", padx=3, pady=3)

        input_frame.columnconfigure(1, weight=1)
        button_row = ttk.Frame(input_frame)
        button_row.grid(
            row=len(ModelService.NUMERIC_FEATURES) + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 4),
        )
        ttk.Button(
            button_row,
            text="Lấy dòng đang chọn",
            command=self._use_selected_training_row,
        ).pack(side="left")
        ttk.Button(
            button_row,
            text="Dự đoán",
            command=predict_command,
        ).pack(side="right")
        ttk.Label(
            input_frame,
            textvariable=result_var,
            font=("Segoe UI", 13, "bold"),
        ).grid(
            row=len(ModelService.NUMERIC_FEATURES) + 2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(8, 0),
        )
        return agent_input

    def _create_evaluation_tab(self):
        """Tạo bảng đánh giá, Distribution Plot và đồ thị chọn bậc."""
        ttk.Label(
            self.evaluation_tab,
            text=(
                "Distribution Plot so sánh tổng Event thực tế và dự đoán "
                "trên dữ liệu đã dùng xây dựng mô hình."
            ),
        ).pack(anchor="w", pady=(0, 5))

        plot_frame = ttk.Frame(self.evaluation_tab)
        plot_frame.pack(fill="both", expand=True)
        self.evaluation_figure = Figure(figsize=(12, 3.8), dpi=100)
        self.linear_evaluation_axis = self.evaluation_figure.add_subplot(121)
        self.polynomial_evaluation_axis = self.evaluation_figure.add_subplot(122)
        self.evaluation_canvas = FigureCanvasTkAgg(
            self.evaluation_figure, master=plot_frame
        )
        self.evaluation_canvas.get_tk_widget().pack(fill="both", expand=True)

        table_frame = ttk.LabelFrame(
            self.evaluation_tab,
            text="Thang đo đánh giá mức độ phù hợp của mô hình",
            padding=6,
        )
        table_frame.pack(fill="both", expand=True, pady=(8, 0))

        evaluation_notebook = ttk.Notebook(table_frame)
        evaluation_notebook.pack(fill="both", expand=True)
        current_frame = ttk.Frame(evaluation_notebook)
        split_frame = ttk.Frame(evaluation_notebook)
        cross_validation_frame = ttk.Frame(evaluation_notebook)
        evaluation_notebook.add(current_frame, text="1. Đánh giá hiện tại")
        evaluation_notebook.add(split_frame, text="2. Train/Test Split 80/20")
        evaluation_notebook.add(
            cross_validation_frame,
            text="3. Kiểm chứng chéo K-Fold",
        )

        columns = ("model", "degree", "sample_count", "mse", "r_squared")
        self.metric_tree = ttk.Treeview(
            current_frame,
            columns=columns,
            show="headings",
            height=3,
        )
        headings = {
            "model": "Mô hình",
            "degree": "Bậc",
            "sample_count": "Số mẫu",
            "mse": "MSE",
            "r_squared": "R²",
        }
        for column in columns:
            self.metric_tree.heading(column, text=headings[column])
            self.metric_tree.column(
                column,
                width=180,
                anchor="center",
            )
        self._add_scrollbars(current_frame, self.metric_tree)

        split_columns = (
            "model",
            "dataset",
            "sample_count",
            "mse",
            "r_squared",
        )
        self.split_metric_tree = ttk.Treeview(
            split_frame,
            columns=split_columns,
            show="headings",
            height=4,
        )
        split_headings = {
            "model": "Mô hình",
            "dataset": "Tập dữ liệu",
            "sample_count": "Số mẫu",
            "mse": "MSE",
            "r_squared": "R²",
        }
        for column in split_columns:
            self.split_metric_tree.heading(column, text=split_headings[column])
            self.split_metric_tree.column(column, width=180, anchor="center")
        self._add_scrollbars(split_frame, self.split_metric_tree)

        cv_content = ttk.Panedwindow(
            cross_validation_frame,
            orient="horizontal",
        )
        cv_content.pack(fill="both", expand=True)
        degree_frame = ttk.LabelFrame(
            cv_content,
            text="Chọn bậc hồi quy đa thức",
            padding=4,
        )
        cv_table_frame = ttk.Frame(cv_content)
        cv_content.add(degree_frame, weight=1)
        cv_content.add(cv_table_frame, weight=2)

        self.degree_figure = Figure(figsize=(5, 2.5), dpi=100)
        self.degree_axis = self.degree_figure.add_subplot(111)
        self.degree_canvas = FigureCanvasTkAgg(
            self.degree_figure,
            master=degree_frame,
        )
        self.degree_canvas.get_tk_widget().pack(fill="both", expand=True)

        cv_columns = (
            "model",
            "fold",
            "train_count",
            "test_count",
            "mse",
            "r_squared",
        )
        self.cv_metric_tree = ttk.Treeview(
            cv_table_frame,
            columns=cv_columns,
            show="headings",
            height=6,
        )
        cv_headings = {
            "model": "Mô hình",
            "fold": "Lần kiểm chứng",
            "train_count": "Mẫu Train",
            "test_count": "Mẫu Test",
            "mse": "MSE Test",
            "r_squared": "R² Test",
        }
        for column in cv_columns:
            self.cv_metric_tree.heading(column, text=cv_headings[column])
            self.cv_metric_tree.column(column, width=165, anchor="center")
        self._add_scrollbars(cv_table_frame, self.cv_metric_tree)

    def reload_dataset(self):
        """Reload Agent/day data and rebuild the model after a CSV import."""
        if not self.csv_path.exists():
            self.status_var.set("Chưa có CSV sạch để xây dựng mô hình.")
            return
        try:
            dataset = EdaService.load_dataset(self.csv_path)
            self.summary = EdaService.aggregate_agent_day(dataset).reset_index(drop=True)
            self._show_training_rows()
            self.train_model()
        except (OSError, ValueError, KeyError, ImportError) as error:
            self.status_var.set(f"Không tải được dữ liệu mô hình: {error}")

    def train_model(self):
        """Huấn luyện HQTT/HQĐT và chạy ba nhóm đánh giá trên dữ liệu cũ."""
        try:
            # Mô hình chính fit trên 100% mẫu có log để phục vụ dự đoán.
            self.model_result = ModelService.train(self.summary)
            # Chọn bậc bằng cùng một split; tiêu chí là MSE test nhỏ nhất.
            self.degree_selection_result = (
                ModelService.select_polynomial_degree(self.summary)
            )
            self.polynomial_degree = self.degree_selection_result[
                "selected_degree"
            ]
            candidate_degrees = [
                row["degree"]
                for row in self.degree_selection_result["comparisons"]
            ]
            # Pipeline bậc 1-10 chỉ fit trên dữ liệu cũ. Tab độc lập chỉ predict,
            # không fit, để đo khả năng chuyển sang bộ dữ liệu mới.
            self.polynomial_candidate_results = (
                ModelService.train_polynomial_candidates(
                    self.summary,
                    degrees=candidate_degrees,
                )
            )
            self.polynomial_result = self.polynomial_candidate_results[
                self.polynomial_degree
            ]
            self.train_test_result = ModelService.evaluate_train_test(
                self.summary,
                test_size=0.2,
                random_state=0,
            )
            self.polynomial_train_test_result = (
                ModelService.evaluate_train_test(
                    self.summary,
                    test_size=0.2,
                    random_state=0,
                    polynomial_degree=self.polynomial_degree,
                )
            )
            self.cross_validation_result = (
                ModelService.evaluate_cross_validation(
                    self.summary,
                    n_splits=5,
                    random_state=0,
                )
            )
            self.polynomial_cross_validation_result = (
                ModelService.evaluate_cross_validation(
                    self.summary,
                    n_splits=5,
                    random_state=0,
                    polynomial_degree=self.polynomial_degree,
                )
            )
        except (ValueError, TypeError) as error:
            self.model_result = None
            self.polynomial_result = None
            self.polynomial_candidate_results = {}
            self.polynomial_degree = None
            self.degree_selection_result = None
            self.train_test_result = None
            self.polynomial_train_test_result = None
            self.cross_validation_result = None
            self.polynomial_cross_validation_result = None
            self.status_var.set(f"Không huấn luyện được mô hình: {error}")
            messagebox.showerror("Lỗi huấn luyện", str(error))
            return

        agents = sorted(self.summary["agent_name"].dropna().astype(str).unique())
        self.agent_input.configure(values=agents)
        self.polynomial_agent_input.configure(values=agents)
        self.status_var.set(
            f"Đã huấn luyện HQTT và HQĐT bậc {self.polynomial_degree} "
            f"bằng {len(self.model_result.comparison)} dòng Agent/ngày có log"
        )
        self._show_training_rows()
        self._show_metrics()
        self._draw_distribution_plot()
        self._draw_degree_selection_plot()
        if not self.summary.empty:
            first_observed = self.summary.index[
                self.summary["total_events"].gt(0)
            ]
            self._fill_inputs(int(first_observed[0]) if len(first_observed) else 0)

    def _show_training_rows(self):
        """Hiển thị thực tế/dự đoán; ngày không log được quy ước dự đoán 0."""
        for item in self.training_tree.get_children():
            self.training_tree.delete(item)

        linear_predictions = pd.Series(
            index=self.summary.index,
            dtype="float64",
        )
        polynomial_predictions = pd.Series(
            index=self.summary.index,
            dtype="float64",
        )
        target_values = pd.to_numeric(
            self.summary[ModelService.TARGET], errors="coerce"
        )
        no_log_mask = target_values.eq(0)
        linear_predictions.loc[no_log_mask] = 0.0
        polynomial_predictions.loc[no_log_mask] = 0.0
        if self.model_result is not None and not self.summary.empty:
            has_log_mask = target_values.gt(0)
            inputs = self.summary.loc[has_log_mask, ModelService.INPUT_FEATURES]
            if not inputs.empty:
                linear_predictions.loc[has_log_mask] = (
                    self.model_result.pipeline.predict(inputs)
                )
                if self.polynomial_result is not None:
                    polynomial_predictions.loc[has_log_mask] = (
                        self.polynomial_result.pipeline.predict(inputs)
                    )

        for index, row in self.summary.iterrows():
            values = [row["agent_name"], self._format_date(row.get("event_date"))]
            for feature in ModelService.NUMERIC_FEATURES:
                values.append(self._format_value(row[feature]))
            values.append(self._format_value(row[ModelService.TARGET]))
            linear_prediction = linear_predictions.loc[index]
            polynomial_prediction = polynomial_predictions.loc[index]
            if no_log_mask.loc[index]:
                values.extend(("0", "0"))
            else:
                for prediction in (
                    linear_prediction,
                    polynomial_prediction,
                ):
                    values.append(
                        self._format_decimal(prediction, 2)
                        if pd.notna(prediction)
                        else "-"
                    )
            self.training_tree.insert("", "end", iid=str(index), values=values)

    def _show_metrics(self):
        """Đưa MSE/R² của 100%, Train/Test và K-Fold vào ba bảng."""
        for item in self.metric_tree.get_children():
            self.metric_tree.delete(item)
        for item in self.split_metric_tree.get_children():
            self.split_metric_tree.delete(item)
        for item in self.cv_metric_tree.get_children():
            self.cv_metric_tree.delete(item)
        full_models = (
            ("HQTT đa biến", "1", self.model_result),
            (
                "HQĐT",
                str(self.polynomial_degree),
                self.polynomial_result,
            ),
        )
        for model_name, degree, result in full_models:
            self.metric_tree.insert(
                "",
                "end",
                values=(
                    model_name,
                    degree,
                    len(result.comparison),
                    self._format_decimal(result.mse, 4),
                    self._format_decimal(result.r_squared, 6),
                ),
            )

        split_labels = {
            "train": "Training 80%",
            "test": "Testing 20%",
        }
        split_models = (
            ("HQTT đa biến", self.train_test_result),
            (
                f"HQĐT bậc {self.polynomial_degree}",
                self.polynomial_train_test_result,
            ),
        )
        for model_name, evaluation in split_models:
            for partition in ("train", "test"):
                metrics = evaluation[partition]
                self.split_metric_tree.insert(
                    "",
                    "end",
                    values=(
                        model_name,
                        split_labels[partition],
                        metrics["sample_count"],
                        self._format_decimal(metrics["mse"], 4),
                        self._format_decimal(metrics["r_squared"], 6),
                    ),
                )

        cv_models = (
            ("HQTT", self.cross_validation_result),
            (
                f"HQĐT bậc {self.polynomial_degree}",
                self.polynomial_cross_validation_result,
            ),
        )
        for model_name, evaluation in cv_models:
            for fold in evaluation["folds"]:
                self.cv_metric_tree.insert(
                    "",
                    "end",
                    values=(
                        model_name,
                        f"Fold {fold['fold']}",
                        fold["train_count"],
                        fold["test_count"],
                        self._format_decimal(fold["mse"], 4),
                        self._format_decimal(fold["r_squared"], 6),
                    ),
                )
            self.cv_metric_tree.insert(
                "",
                "end",
                values=(
                    model_name,
                    "Trung bình",
                    "-",
                    "-",
                    self._format_decimal(evaluation["mean_mse"], 4),
                    self._format_decimal(evaluation["mean_r_squared"], 6),
                ),
            )

    def _draw_distribution_plot(self):
        """So sánh mật độ total_events thực tế và dự đoán của hai mô hình."""
        plots = (
            (
                self.linear_evaluation_axis,
                self.model_result.comparison,
                "Hồi quy tuyến tính đa biến",
            ),
            (
                self.polynomial_evaluation_axis,
                self.polynomial_result.comparison,
                f"Hồi quy đa thức bậc {self.polynomial_degree}",
            ),
        )
        for axis, comparison, title in plots:
            axis.clear()
            sns.kdeplot(
                data=comparison,
                x="actual",
                ax=axis,
                color="#D62728",
                linewidth=2,
                label="Thực tế",
                warn_singular=False,
            )
            sns.kdeplot(
                data=comparison,
                x="predicted",
                ax=axis,
                color="#1F77B4",
                linewidth=2,
                label="Dự đoán",
                warn_singular=False,
            )
            axis.set_title(f"Distribution Plot: {title}")
            axis.set_xlabel("total_events")
            axis.set_ylabel("Mật độ")
            axis.grid(alpha=0.25)
            axis.legend()
        self.evaluation_figure.tight_layout()
        self.evaluation_canvas.draw_idle()

    def _draw_degree_selection_plot(self):
        """Vẽ MSE train/test bậc 1-10 và đánh dấu bậc HQĐT được chọn."""
        axis = self.degree_axis
        axis.clear()
        comparisons = self.degree_selection_result["comparisons"]
        degrees = [row["degree"] for row in comparisons]
        train_mse = [row["train_mse"] for row in comparisons]
        test_mse = [row["test_mse"] for row in comparisons]
        axis.plot(degrees, train_mse, marker="o", label="MSE Train")
        axis.plot(degrees, test_mse, marker="o", label="MSE Test")
        axis.axvline(
            self.polynomial_degree,
            color="#16A34A",
            linestyle="--",
            label=f"Chọn bậc {self.polynomial_degree}",
        )
        axis.set_title("MSE Train/Test theo bậc")
        axis.set_xlabel("Bậc đa thức")
        axis.set_ylabel("MSE (thang log)")
        axis.set_yscale("log")
        axis.set_xticks(degrees)
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
        self.degree_figure.tight_layout()
        self.degree_canvas.draw_idle()

    def _use_selected_training_row(self):
        """Đổ dòng đang chọn trong bảng vào cả hai form dự đoán."""
        selection = self.training_tree.selection()
        if not selection:
            messagebox.showwarning(
                "Chưa chọn dòng",
                "Hãy chọn một dòng trong tab Dữ liệu & huấn luyện trước.",
            )
            return
        self._fill_inputs(int(selection[0]))

    def _fill_inputs(self, index):
        """Điền một dòng Agent/ngày vào các biến nhập liệu Tkinter."""
        row = self.summary.iloc[index]
        for input_vars in (self.input_vars, self.polynomial_input_vars):
            input_vars["agent_name"].set(str(row["agent_name"]))
            for feature in ModelService.NUMERIC_FEATURES:
                value = row[feature]
                input_vars[feature].set(
                    "" if pd.isna(value) else str(value)
                )
        self.prediction_var.set("Tổng Event HQTT: -")
        self.polynomial_prediction_var.set(
            f"Tổng Event HQĐT bậc {self.polynomial_degree}: -"
        )

    def predict_one(self):
        """Dự đoán một mẫu nhập tay bằng Pipeline HQTT đã fit."""
        if self.model_result is None:
            messagebox.showwarning("Chưa có mô hình", "Hãy huấn luyện mô hình trước.")
            return
        values = {name: variable.get() for name, variable in self.input_vars.items()}
        try:
            prediction = ModelService.predict(self.model_result, values)
        except ValueError as error:
            messagebox.showerror("Dữ liệu không hợp lệ", str(error))
            return
        formatted = (
            f"{prediction:,.2f}"
            .replace(",", "_")
            .replace(".", ",")
            .replace("_", ".")
        )
        self.prediction_var.set(f"Tổng Event HQTT: {formatted}")

    def predict_polynomial(self):
        """Dự đoán cùng mẫu nhập tay bằng Pipeline HQĐT đã fit."""
        if self.polynomial_result is None:
            messagebox.showwarning(
                "Chưa có mô hình",
                "Hãy huấn luyện mô hình trước.",
            )
            return
        values = {
            name: variable.get()
            for name, variable in self.polynomial_input_vars.items()
        }
        try:
            prediction = ModelService.predict(
                self.polynomial_result,
                values,
            )
        except ValueError as error:
            messagebox.showerror("Dữ liệu không hợp lệ", str(error))
            return
        formatted = self._format_decimal(prediction, 2)
        self.polynomial_prediction_var.set(
            f"Tổng Event HQĐT bậc {self.polynomial_degree}: "
            f"{formatted}"
        )

    @staticmethod
    def _format_date(value):
        """Định dạng ngày cho bảng dữ liệu huấn luyện."""
        if pd.isna(value):
            return "-"
        return pd.Timestamp(value).strftime("%Y-%m-%d")

    @staticmethod
    def _format_value(value):
        """Hiển thị missing bằng dấu gạch và giữ giá trị số dễ đọc."""
        if pd.isna(value):
            return "-"
        numeric = float(value)
        return str(int(numeric)) if numeric.is_integer() else f"{numeric:.2f}"

    @staticmethod
    def _format_decimal(value, digits):
        """Định dạng số theo số chữ số và dấu phẩy thập phân."""
        formatted = f"{float(value):,.{digits}f}"
        return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
