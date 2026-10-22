"""Tests for the Agent/day regression Pipeline."""

import unittest

import pandas as pd

from src.services.model_service import ModelService


class ModelServiceTests(unittest.TestCase):
    def setUp(self):
        rows = []
        agents = ["A", "B", "C", "D"]
        for index in range(12):
            total = index + 1
            high = index % 4
            rows.append(
                {
                    "agent_name": agents[index % 4],
                    "event_date": pd.Timestamp("2026-10-01")
                    + pd.Timedelta(days=index),
                    "total_events": total,
                    "high_level_alerts": high,
                    "unique_rules": max(1, total // 2),
                    "unique_event_ids": max(1, total // 3),
                    "unique_source_ips": index % 3,
                    "unique_users": index % 5,
                    "avg_rule_level": None if index == 0 else 7 + high,
                    "max_rule_level": None if index == 0 else 9 + high,
                }
            )
        self.summary = pd.DataFrame(rows)

    def test_train_builds_pipeline_formula_and_comparison(self):
        result = ModelService.train(self.summary)

        self.assertEqual(len(self.summary), len(result.comparison))
        self.assertIn("total_events dự đoán", result.formula)
        self.assertEqual(
            len(result.feature_names), len(ModelService.NUMERIC_FEATURES) + 3
        )
        self.assertTrue(any(name.startswith("agent_name_") for name in result.feature_names))
        self.assertEqual("A", result.reference_agent)
        self.assertGreater(result.r_squared, 0.99)
        self.assertGreaterEqual(result.mse, 0.0)

    def test_predict_uses_fitted_pipeline(self):
        result = ModelService.train(self.summary)
        values = self.summary.iloc[3][ModelService.INPUT_FEATURES].to_dict()
        prediction = ModelService.predict(result, values)
        self.assertIsInstance(prediction, float)

    def test_train_excludes_agent_days_without_logs(self):
        empty_day = self.summary.iloc[[0]].copy()
        empty_day["total_events"] = 0
        empty_day[ModelService.NUMERIC_FEATURES] = 0
        summary = pd.concat([empty_day, self.summary], ignore_index=True)

        result = ModelService.train(summary)

        self.assertEqual(len(self.summary), len(result.comparison))
        self.assertTrue(result.comparison["actual"].gt(0).all())

    def test_train_test_evaluation_uses_80_20_split(self):
        evaluation = ModelService.evaluate_train_test(self.summary)

        self.assertEqual(9, evaluation["train"]["sample_count"])
        self.assertEqual(3, evaluation["test"]["sample_count"])
        self.assertGreaterEqual(evaluation["train"]["mse"], 0.0)
        self.assertGreaterEqual(evaluation["test"]["mse"], 0.0)

    def test_cross_validation_reports_each_fold_and_average(self):
        evaluation = ModelService.evaluate_cross_validation(
            self.summary, n_splits=3
        )

        self.assertEqual(3, len(evaluation["folds"]))
        self.assertTrue(all(fold["test_count"] == 4 for fold in evaluation["folds"]))
        self.assertGreaterEqual(evaluation["mean_mse"], 0.0)

    def test_polynomial_model_and_degree_selection(self):
        selection = ModelService.select_polynomial_degree(
            self.summary,
            degrees=range(1, 4),
        )
        result = ModelService.train(
            self.summary,
            polynomial_degree=selection["selected_degree"],
        )
        numeric_steps = (
            result.pipeline.named_steps["preprocessor"]
            .named_transformers_["numeric"]
            .named_steps
        )

        self.assertEqual(3, len(selection["comparisons"]))
        self.assertIn(selection["selected_degree"], (2, 3))
        self.assertIn("scaler", numeric_steps)
        self.assertIn("polynomial", numeric_steps)

    def test_external_evaluation_does_not_refit_pipeline(self):
        result = ModelService.train(self.summary)
        coefficients_before = result.coefficients.copy()

        evaluation = ModelService.evaluate_external(self.summary, result)

        self.assertEqual(len(self.summary), evaluation["sample_count"])
        self.assertEqual(len(self.summary), len(evaluation["comparison"]))
        self.assertGreaterEqual(evaluation["mse"], 0.0)
        pd.testing.assert_frame_equal(coefficients_before, result.coefficients)

    def test_train_rejects_missing_columns(self):
        with self.assertRaisesRegex(ValueError, "thiếu cột"):
            ModelService.train(self.summary.drop(columns=["total_events"]))


if __name__ == "__main__":
    unittest.main()
