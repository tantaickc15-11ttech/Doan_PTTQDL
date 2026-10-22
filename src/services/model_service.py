"""Xây dựng, dự đoán và đánh giá các mô hình hồi quy theo Agent/ngày.

KỸ THUẬT: Pipeline, điền khuyết, One-Hot Encoding, hồi quy tuyến tính đa
biến/đa thức, Train/Test Split và K-Fold.
VẤN ĐỀ: đầu vào gồm cả số lẫn chữ và lúc dự đoán phải được xử lý giống hệt
lúc huấn luyện.
TÁC DỤNG: gom tiền xử lý và mô hình vào một quy trình tái sử dụng, đồng thời
đánh giá bằng MSE và R².
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, PolynomialFeatures, StandardScaler


@dataclass
class ModelResult:
    """Đóng gói Pipeline đã fit, dự đoán và các thang đo để UI sử dụng."""

    pipeline: Pipeline
    feature_names: list[str]
    coefficients: pd.DataFrame
    comparison: pd.DataFrame
    intercept: float
    formula: str
    reference_agent: str
    r_squared: float
    mse: float
    mae: float
    rmse: float


class ModelService:
    """Nơi duy nhất thực hiện fit, predict và đánh giá mô hình trong ứng dụng."""

    TARGET = "total_events"
    CATEGORICAL_FEATURES = ["agent_name"]
    NUMERIC_FEATURES = [
        "high_level_alerts",
        "unique_rules",
        "unique_event_ids",
        "unique_source_ips",
        "unique_users",
        "avg_rule_level",
        "max_rule_level",
    ]
    INPUT_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES

    @classmethod
    def train(
        cls,
        summary: pd.DataFrame,
        polynomial_degree: int | None = None,
    ) -> ModelResult:
        """Huấn luyện Pipeline và trả về mô hình cùng kết quả trên tập đã học.

        ``fit(X, y)`` là bước để mô hình học hệ số từ biến độc lập X và biến
        mục tiêu ``total_events``; đây không phải bước dự đoán.
        """
        missing = [
            column
            for column in cls.INPUT_FEATURES + [cls.TARGET]
            if column not in summary.columns
        ]
        if missing:
            raise ValueError(f"Dữ liệu thiếu cột: {', '.join(missing)}")
        if summary.empty:
            raise ValueError("Không có dữ liệu Agent/ngày để huấn luyện.")

        data = summary.copy().reset_index(drop=True)
        target = pd.to_numeric(data[cls.TARGET], errors="coerce")
        # KỸ THUẬT - lọc mẫu hợp lệ.
        # VẤN ĐỀ - total_events=0 là dòng giữ chỗ cho ngày không có log.
        # TÁC DỤNG - không cho dữ liệu giả làm sai các hệ số hồi quy.
        valid = target.notna() & target.gt(0)
        data = data.loc[valid].reset_index(drop=True)
        target = target.loc[valid].reset_index(drop=True)
        if len(data) < 2 or target.nunique() < 2:
            raise ValueError("Cần ít nhất 2 mẫu và biến mục tiêu phải có thay đổi.")

        # KỸ THUẬT - Pipeline ghép tiền xử lý và hồi quy thành một quy trình.
        # VẤN ĐỀ - xử lý thủ công dễ làm fit và predict dùng quy tắc khác nhau.
        # TÁC DỤNG - mọi dữ liệu đều qua đúng điền khuyết/One-Hot trước mô hình.
        # SimpleImputer(median) học trung vị từng cột số ở tập train rồi dùng
        # trung vị đó điền ô thiếu; nó không tự tạo dữ liệu cho cả dòng rỗng.
        numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
        if polynomial_degree is not None:
            if polynomial_degree < 1:
                raise ValueError("Bậc đa thức phải từ 1 trở lên.")
            # Chuẩn hóa trước khi sinh x², x³... để giảm chênh lệch thang đo.
            numeric_steps.append(("scaler", StandardScaler()))
            numeric_steps.append(
                (
                    "polynomial",
                    PolynomialFeatures(
                        degree=polynomial_degree,
                        include_bias=False,
                    ),
                )
            )
        numeric_pipeline = Pipeline(steps=numeric_steps)
        # One-Hot Encoding biến agent_name thành các cột 0/1. drop="first" bỏ
        # một Agent làm mốc để tránh dummy-variable trap; Agent mốc có toàn 0.
        # Agent lạ được ignore để dự đoán không lỗi nhưng cũng được mã hóa toàn 0.
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                (
                    "one_hot",
                    OneHotEncoder(
                        drop="first",
                        handle_unknown="ignore",
                        sparse_output=False,
                    ),
                ),
            ]
        )
        # ColumnTransformer xử lý đúng nhánh số/phân loại rồi ghép thành ma trận số.
        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", numeric_pipeline, cls.NUMERIC_FEATURES),
                ("agent", categorical_pipeline, cls.CATEGORICAL_FEATURES),
            ],
            verbose_feature_names_out=False,
        )
        model_pipeline = Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("regression", LinearRegression()),
            ]
        )

        inputs = data[cls.INPUT_FEATURES]
        # HUẤN LUYỆN: fit học trung vị, danh sách Agent và các hệ số hồi quy.
        model_pipeline.fit(inputs, target)
        # DỰ ĐOÁN: predict áp dụng những gì đã học, không học lại mô hình.
        predicted = model_pipeline.predict(inputs)

        feature_names = list(
            model_pipeline.named_steps["preprocessor"].get_feature_names_out()
        )
        one_hot = (
            model_pipeline.named_steps["preprocessor"]
            .named_transformers_["agent"]
            .named_steps["one_hot"]
        )
        dropped_index = int(one_hot.drop_idx_[0])
        reference_agent = str(one_hot.categories_[0][dropped_index])
        regression = model_pipeline.named_steps["regression"]
        coefficient_values = np.asarray(regression.coef_, dtype="float64")
        coefficients = pd.DataFrame(
            {"feature": feature_names, "coefficient": coefficient_values}
        )
        intercept = float(regression.intercept_)

        comparison_columns = [
            column
            for column in ["agent_name", "event_date"]
            if column in data.columns
        ]
        comparison = data[comparison_columns].copy()
        comparison["actual"] = target.to_numpy(dtype="float64")
        comparison["predicted"] = predicted
        comparison["error"] = comparison["actual"] - comparison["predicted"]

        # ĐÁNH GIÁ: residual=thực tế-dự đoán; MSE là trung bình residual²;
        # R² đo tỷ lệ biến thiên của total_events được mô hình giải thích.
        residual = target.to_numpy(dtype="float64") - predicted
        mae = float(np.mean(np.abs(residual)))
        mse = float(np.mean(np.square(residual)))
        rmse = float(np.sqrt(mse))
        total_variation = float(
            np.sum(np.square(target.to_numpy(dtype="float64") - target.mean()))
        )
        r_squared = (
            1.0 - float(np.sum(np.square(residual))) / total_variation
            if total_variation > 0
            else float("nan")
        )

        return ModelResult(
            pipeline=model_pipeline,
            feature_names=feature_names,
            coefficients=coefficients,
            comparison=comparison,
            intercept=intercept,
            formula=cls.format_formula(intercept, coefficients),
            reference_agent=reference_agent,
            r_squared=r_squared,
            mse=mse,
            mae=mae,
            rmse=rmse,
        )

    @classmethod
    def predict(cls, result: ModelResult, values: dict) -> float:
        """Dự đoán total_events cho một mẫu bằng Pipeline đã fit, không học lại."""
        row = {"agent_name": str(values.get("agent_name", ""))}
        for feature in cls.NUMERIC_FEATURES:
            try:
                row[feature] = float(values[feature])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"Giá trị {feature} không hợp lệ.") from error
        return float(result.pipeline.predict(pd.DataFrame([row]))[0])

    @classmethod
    def train_polynomial_candidates(
        cls,
        summary: pd.DataFrame,
        degrees=range(1, 11),
    ) -> dict[int, ModelResult]:
        """Fit reference polynomial Pipelines using only the training dataset."""
        return {
            int(degree): cls.train(summary, polynomial_degree=int(degree))
            for degree in degrees
        }

    @classmethod
    def _rows_with_logs(cls, summary: pd.DataFrame) -> pd.DataFrame:
        """Return only observed Agent/day rows that have a target value."""
        data = summary.copy().reset_index(drop=True)
        target = pd.to_numeric(data[cls.TARGET], errors="coerce")
        return data.loc[target.notna() & target.gt(0)].reset_index(drop=True)

    @classmethod
    def evaluate_train_test(
        cls,
        summary: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 0,
        polynomial_degree: int | None = None,
    ) -> dict:
        """Fit trên 80% rồi đánh giá đúng mô hình đó trên 20% chưa được học.

        Tập test không gọi ``fit``; nó chỉ qua ``predict`` rồi so với y_test.
        """
        data = cls._rows_with_logs(summary)
        train_data, test_data = train_test_split(
            data,
            test_size=test_size,
            random_state=random_state,
        )
        # Chỉ phần train được dùng để tìm công thức/hệ số.
        trained = cls.train(
            train_data,
            polynomial_degree=polynomial_degree,
        )
        y_test = pd.to_numeric(test_data[cls.TARGET], errors="coerce")
        # Phần test đi vào công thức đã học để đo khả năng tổng quát hóa.
        y_test_predicted = trained.pipeline.predict(
            test_data[cls.INPUT_FEATURES]
        )
        return {
            "train": {
                "sample_count": len(train_data),
                "mse": trained.mse,
                "r_squared": trained.r_squared,
            },
            "test": {
                "sample_count": len(test_data),
                "mse": float(mean_squared_error(y_test, y_test_predicted)),
                "r_squared": float(r2_score(y_test, y_test_predicted)),
            },
        }

    @classmethod
    def evaluate_cross_validation(
        cls,
        summary: pd.DataFrame,
        n_splits: int = 5,
        random_state: int = 0,
        polynomial_degree: int | None = None,
    ) -> dict:
        """Luân phiên nhiều tập test bằng K-Fold rồi lấy kết quả trung bình.

        Mỗi fold tạo Pipeline mới và chỉ fit trên phần train của fold đó.
        """
        data = cls._rows_with_logs(summary)
        if len(data) < n_splits:
            raise ValueError(
                f"Cần ít nhất {n_splits} mẫu để kiểm chứng chéo."
            )

        folds = []
        splitter = KFold(
            n_splits=n_splits,
            shuffle=True,
            random_state=random_state,
        )
        for fold_number, (train_indices, test_indices) in enumerate(
            splitter.split(data), start=1
        ):
            train_data = data.iloc[train_indices].reset_index(drop=True)
            test_data = data.iloc[test_indices].reset_index(drop=True)
            trained = cls.train(
                train_data,
                polynomial_degree=polynomial_degree,
            )
            y_test = pd.to_numeric(test_data[cls.TARGET], errors="coerce")
            y_test_predicted = trained.pipeline.predict(
                test_data[cls.INPUT_FEATURES]
            )
            folds.append(
                {
                    "fold": fold_number,
                    "train_count": len(train_data),
                    "test_count": len(test_data),
                    "mse": float(mean_squared_error(y_test, y_test_predicted)),
                    "r_squared": float(r2_score(y_test, y_test_predicted)),
                }
            )

        return {
            "folds": folds,
            "mean_mse": float(np.mean([fold["mse"] for fold in folds])),
            "mean_r_squared": float(
                np.mean([fold["r_squared"] for fold in folds])
            ),
        }

    @classmethod
    def evaluate_external(
        cls,
        summary: pd.DataFrame,
        result: ModelResult,
    ) -> dict:
        """Dùng nguyên Pipeline cũ để đánh giá bộ dữ liệu độc lập.

        Chỉ ``predict``, không ``fit``: công thức vẫn học từ 100% dữ liệu cũ.
        """
        data = cls._rows_with_logs(summary)
        if data.empty:
            raise ValueError("Bộ dữ liệu kiểm thử không có dòng phát sinh log.")

        actual = pd.to_numeric(data[cls.TARGET], errors="coerce")
        predicted = result.pipeline.predict(data[cls.INPUT_FEATURES])
        comparison_columns = [
            column
            for column in ("agent_name", "event_date")
            if column in data.columns
        ]
        comparison = data[comparison_columns].copy()
        comparison["actual"] = actual.to_numpy(dtype="float64")
        comparison["predicted"] = predicted
        comparison["error"] = comparison["actual"] - comparison["predicted"]
        mse = float(mean_squared_error(actual, predicted))
        return {
            "sample_count": len(data),
            "comparison": comparison,
            "mae": float(np.mean(np.abs(comparison["error"]))),
            "mse": mse,
            "rmse": float(np.sqrt(mse)),
            "r_squared": float(r2_score(actual, predicted)),
        }

    @classmethod
    def select_polynomial_degree(
        cls,
        summary: pd.DataFrame,
        degrees=range(1, 11),
        test_size: float = 0.2,
        random_state: int = 0,
        minimum_degree: int = 2,
    ) -> dict:
        """So sánh bậc trên cùng một split và chọn MSE test nhỏ nhất.

        Chênh MSE train/test là dấu hiệu overfit để tham khảo; tiêu chí chốt là
        MSE test nhỏ nhất. Bậc 1 bị loại vì trùng bản chất hồi quy tuyến tính.
        """
        comparisons = []
        for degree in degrees:
            evaluation = cls.evaluate_train_test(
                summary,
                test_size=test_size,
                random_state=random_state,
                polynomial_degree=int(degree),
            )
            comparisons.append(
                {
                    "degree": int(degree),
                    "train_mse": evaluation["train"]["mse"],
                    "test_mse": evaluation["test"]["mse"],
                    "train_r_squared": evaluation["train"]["r_squared"],
                    "test_r_squared": evaluation["test"]["r_squared"],
                }
            )
        if not comparisons:
            raise ValueError("Cần ít nhất một bậc đa thức để đánh giá.")
        selectable = [
            row for row in comparisons
            if row["degree"] >= minimum_degree
        ]
        if not selectable:
            raise ValueError(
                f"Không có bậc đa thức từ {minimum_degree} trở lên."
            )
        selected = min(selectable, key=lambda row: row["test_mse"])
        return {
            "selected_degree": selected["degree"],
            "comparisons": comparisons,
        }

    @classmethod
    def format_formula(
        cls, intercept: float, coefficients: pd.DataFrame, precision: int = 6
    ) -> str:
        """Format the learned formula without changing its calculated values."""
        formula = f"{cls.TARGET} dự đoán = {intercept:.{precision}f}"
        for row in coefficients.itertuples(index=False):
            sign = "+" if row.coefficient >= 0 else "−"
            formula += (
                f"\n  {sign} {abs(row.coefficient):.{precision}f}"
                f" × {row.feature}"
            )
        return formula
