"""
Evaluation Engine — Computes detailed model evaluation metrics and visualization data.
All results come from actual model predictions — never fabricated.
"""
import numpy as np
from typing import Dict, Any, Optional
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
    roc_curve, precision_recall_curve, auc,
    mean_absolute_error, mean_squared_error, r2_score,
)


class EvaluationEngine:
    """Compute real evaluation metrics from model predictions."""

    @staticmethod
    def evaluate_classification(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
        class_labels: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Full classification evaluation with metrics and chart data."""
        n_classes = len(np.unique(y_true))
        is_binary = n_classes == 2

        # Core metrics
        metrics = {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
            "precision": round(float(precision_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
            "f1": round(float(f1_score(y_true, y_pred, average="weighted", zero_division=0)), 4),
        }

        # ROC-AUC (requires probability predictions)
        if y_prob is not None:
            try:
                if is_binary:
                    if y_prob.ndim == 2:
                        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_prob[:, 1])), 4)
                    else:
                        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_prob)), 4)
                else:
                    metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_prob, multi_class="ovr", average="weighted")), 4)
            except Exception:
                metrics["roc_auc"] = None

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        labels = class_labels or [str(c) for c in sorted(np.unique(np.concatenate([y_true, y_pred])))]
        cm_data = {
            "matrix": cm.tolist(),
            "labels": labels,
        }

        # Per-class report
        report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        per_class = []
        for label in labels:
            if str(label) in report:
                cls_report = report[str(label)]
                per_class.append({
                    "class": str(label),
                    "precision": round(float(cls_report["precision"]), 4),
                    "recall": round(float(cls_report["recall"]), 4),
                    "f1": round(float(cls_report["f1-score"]), 4),
                    "support": int(cls_report["support"]),
                })

        # ROC curve data (binary)
        roc_curve_data = None
        if y_prob is not None and is_binary:
            try:
                prob_positive = y_prob[:, 1] if y_prob.ndim == 2 else y_prob
                fpr, tpr, _ = roc_curve(y_true, prob_positive)
                roc_curve_data = {
                    "fpr": [round(float(v), 4) for v in fpr],
                    "tpr": [round(float(v), 4) for v in tpr],
                    "auc": round(float(auc(fpr, tpr)), 4),
                }
            except Exception:
                pass

        # Precision-Recall curve data (binary)
        pr_curve_data = None
        if y_prob is not None and is_binary:
            try:
                prob_positive = y_prob[:, 1] if y_prob.ndim == 2 else y_prob
                precision_arr, recall_arr, _ = precision_recall_curve(y_true, prob_positive)
                pr_curve_data = {
                    "precision": [round(float(v), 4) for v in precision_arr],
                    "recall": [round(float(v), 4) for v in recall_arr],
                    "auc": round(float(auc(recall_arr, precision_arr)), 4),
                }
            except Exception:
                pass

        # Class distribution
        unique, counts = np.unique(y_true, return_counts=True)
        class_dist = {str(u): int(c) for u, c in zip(unique, counts)}

        return {
            "metrics": metrics,
            "confusion_matrix": cm_data,
            "per_class_report": per_class,
            "roc_curve": roc_curve_data,
            "pr_curve": pr_curve_data,
            "class_distribution": class_dist,
            "n_samples": len(y_true),
        }

    @staticmethod
    def evaluate_regression(
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> Dict[str, Any]:
        """Full regression evaluation with metrics and chart data."""
        metrics = {
            "mae": round(float(mean_absolute_error(y_true, y_pred)), 4),
            "mse": round(float(mean_squared_error(y_true, y_pred)), 4),
            "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
            "r2": round(float(r2_score(y_true, y_pred)), 4),
        }

        # Residual analysis
        residuals = y_true - y_pred
        residual_stats = {
            "mean": round(float(np.mean(residuals)), 4),
            "std": round(float(np.std(residuals)), 4),
            "min": round(float(np.min(residuals)), 4),
            "max": round(float(np.max(residuals)), 4),
        }

        # Sample data for scatter plot (predicted vs actual)
        max_points = 500
        if len(y_true) > max_points:
            indices = np.random.choice(len(y_true), max_points, replace=False)
            y_true_sample = y_true[indices]
            y_pred_sample = y_pred[indices]
            residuals_sample = residuals[indices]
        else:
            y_true_sample = y_true
            y_pred_sample = y_pred
            residuals_sample = residuals

        scatter_data = {
            "actual": [round(float(v), 4) for v in y_true_sample],
            "predicted": [round(float(v), 4) for v in y_pred_sample],
        }

        residual_data = {
            "predicted": [round(float(v), 4) for v in y_pred_sample],
            "residuals": [round(float(v), 4) for v in residuals_sample],
        }

        return {
            "metrics": metrics,
            "residual_stats": residual_stats,
            "scatter_data": scatter_data,
            "residual_data": residual_data,
            "n_samples": len(y_true),
        }

    @classmethod
    def evaluate(
        cls,
        model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
        task_type: str,
        class_labels: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Unified evaluation entry point."""
        y_pred = model.predict(X_test)

        if "classification" in task_type:
            y_prob = None
            if hasattr(model, "predict_proba"):
                try:
                    y_prob = model.predict_proba(X_test)
                except Exception:
                    pass
            return cls.evaluate_classification(y_test, y_pred, y_prob, class_labels)
        else:
            return cls.evaluate_regression(y_test, y_pred)
