"""
AutoML Engine — Trains multiple ML models and produces a real leaderboard.
Supports classification (LogisticRegression, RandomForest, XGBoost) and
regression (LinearRegression, RandomForest, XGBoost).
All metrics come from actual cross-validation — never fabricated.
"""
import os
import time
import json
import numpy as np
import pandas as pd
import joblib
from typing import Dict, Any, List, Optional, Callable
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.model_selection import cross_validate, StratifiedKFold, KFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    mean_absolute_error, mean_squared_error, r2_score,
)
from xgboost import XGBClassifier, XGBRegressor


class AutoMLEngine:
    """Train and evaluate multiple ML models using real cross-validation."""

    CLASSIFICATION_MODELS = {
        "logistic_regression": {
            "class": LogisticRegression,
            "params": {"max_iter": 1000, "random_state": 42, "n_jobs": -1},
            "display_name": "Logistic Regression",
        },
        "random_forest": {
            "class": RandomForestClassifier,
            "params": {"n_estimators": 100, "random_state": 42, "n_jobs": -1},
            "display_name": "Random Forest",
        },
        "xgboost": {
            "class": XGBClassifier,
            "params": {
                "n_estimators": 100, "random_state": 42, "n_jobs": -1,
                "eval_metric": "logloss",
                "verbosity": 0,
            },
            "display_name": "XGBoost",
        },
    }

    REGRESSION_MODELS = {
        "linear_regression": {
            "class": LinearRegression,
            "params": {"n_jobs": -1},
            "display_name": "Linear Regression",
        },
        "random_forest": {
            "class": RandomForestRegressor,
            "params": {"n_estimators": 100, "random_state": 42, "n_jobs": -1},
            "display_name": "Random Forest",
        },
        "xgboost": {
            "class": XGBRegressor,
            "params": {
                "n_estimators": 100, "random_state": 42, "n_jobs": -1,
                "verbosity": 0,
            },
            "display_name": "XGBoost",
        },
    }

    CLASSIFICATION_SCORING = {
        "accuracy": "accuracy",
        "precision": "precision_weighted",
        "recall": "recall_weighted",
        "f1": "f1_weighted",
        "roc_auc": "roc_auc_ovr_weighted",
    }

    REGRESSION_SCORING = {
        "mae": "neg_mean_absolute_error",
        "mse": "neg_mean_squared_error",
        "r2": "r2",
    }

    @classmethod
    def train_models(
        cls,
        X_train: np.ndarray,
        y_train: np.ndarray,
        task_type: str,
        primary_metric: Optional[str] = None,
        cv_folds: int = 5,
        random_seed: int = 42,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Train all candidate models with cross-validation.
        Returns leaderboard with real metrics.
        """
        is_classification = "classification" in task_type
        models = cls.CLASSIFICATION_MODELS if is_classification else cls.REGRESSION_MODELS
        scoring = cls.CLASSIFICATION_SCORING if is_classification else cls.REGRESSION_SCORING

        if primary_metric is None:
            primary_metric = "f1" if is_classification else "r2"

        # Setup CV
        if is_classification:
            counts = pd.Series(y_train).value_counts()
            min_count = int(counts.min()) if len(counts) > 0 else 0
            if min_count >= 2:
                effective_folds = max(2, min(cv_folds, min_count))
                cv = StratifiedKFold(n_splits=effective_folds, shuffle=True, random_state=random_seed)
            else:
                effective_folds = max(2, min(cv_folds, len(y_train)))
                cv = KFold(n_splits=effective_folds, shuffle=True, random_state=random_seed)
        else:
            effective_folds = max(2, min(cv_folds, len(y_train)))
            cv = KFold(n_splits=effective_folds, shuffle=True, random_state=random_seed)

        leaderboard = []
        trained_models = {}
        total_models = len(models)

        for idx, (model_key, model_config) in enumerate(models.items()):
            if progress_callback:
                progress_callback(
                    progress=(idx / total_models) * 100,
                    message=f"Training {model_config['display_name']}...",
                )

            start_time = time.time()
            try:
                # Create model instance
                model = model_config["class"](**model_config["params"])

                # Cross-validate
                cv_results = cross_validate(
                    model, X_train, y_train,
                    cv=cv, scoring=scoring,
                    return_train_score=False,
                    error_score=np.nan,
                )

                # Extract metrics
                metrics = {}
                cv_scores = {}
                for metric_name, sklearn_name in scoring.items():
                    key = f"test_{metric_name}"
                    if key in cv_results:
                        scores = cv_results[key]
                        # Convert negative scores back
                        if sklearn_name.startswith("neg_"):
                            scores = -scores
                        metrics[metric_name] = round(float(np.nanmean(scores)), 4)
                        cv_scores[metric_name] = [round(float(s), 4) for s in scores if not np.isnan(s)]

                # Add RMSE for regression
                if not is_classification and "mse" in metrics:
                    metrics["rmse"] = round(float(np.sqrt(metrics["mse"])), 4)

                # Fit the final model on all training data
                model.fit(X_train, y_train)

                duration = round(time.time() - start_time, 2)

                leaderboard.append({
                    "algorithm": model_key,
                    "display_name": model_config["display_name"],
                    "metrics": metrics,
                    "cv_scores": cv_scores,
                    "primary_metric_value": metrics.get(primary_metric, 0),
                    "training_duration": duration,
                    "hyperparameters": model_config["params"],
                    "status": "completed",
                })

                trained_models[model_key] = model

            except Exception as e:
                duration = round(time.time() - start_time, 2)
                leaderboard.append({
                    "algorithm": model_key,
                    "display_name": model_config["display_name"],
                    "metrics": {},
                    "cv_scores": {},
                    "primary_metric_value": 0,
                    "training_duration": duration,
                    "hyperparameters": model_config["params"],
                    "status": "failed",
                    "error": str(e),
                })

        # Sort leaderboard by primary metric (descending for most metrics)
        reverse = True
        if primary_metric in ("mae", "mse", "rmse"):
            reverse = False

        leaderboard.sort(key=lambda x: x["primary_metric_value"], reverse=reverse)

        # Add rank
        for i, entry in enumerate(leaderboard):
            entry["rank"] = i + 1

        if progress_callback:
            progress_callback(progress=100, message="Training complete.")

        return {
            "leaderboard": leaderboard,
            "trained_models": trained_models,
            "primary_metric": primary_metric,
            "task_type": task_type,
            "cv_folds": cv_folds,
            "random_seed": random_seed,
        }

    @classmethod
    def train_models_budget(
        cls,
        X_train: np.ndarray,
        y_train: np.ndarray,
        task_type: str,
        budget_seconds: int = 120,
        primary_metric: Optional[str] = None,
        cv_folds: int = 3,
        random_seed: int = 42,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Budget-Aware AutoML using Successive Halving.
        Evaluates models on increasing sample sizes [0.25, 0.60, 1.0],
        eliminating lower-performing candidates at each round.
        Tracks full elimination_log and survival_funnel.
        """
        start_overall_time = time.time()
        is_classification = "classification" in task_type
        all_models = cls.CLASSIFICATION_MODELS if is_classification else cls.REGRESSION_MODELS

        if primary_metric is None:
            primary_metric = "f1" if is_classification else "r2"

        n_total = len(X_train)
        stages = [
            {"round": 1, "fraction": 0.25, "name": "Stage 1 (25% sample)"},
            {"round": 2, "fraction": 0.60, "name": "Stage 2 (60% sample)"},
            {"round": 3, "fraction": 1.00, "name": "Stage 3 (Full dataset)"},
        ]

        active_keys = list(all_models.keys())
        elimination_log = []
        survival_funnel = []
        final_trained_models = {}
        last_stage_scores = {}

        for stage_idx, stage in enumerate(stages):
            round_num = stage["round"]
            fraction = stage["fraction"]
            sample_size = max(min(n_total, 50), int(n_total * fraction))

            if progress_callback:
                progress_callback(
                    progress=int((stage_idx / len(stages)) * 90),
                    message=f"Budget AutoML: {stage['name']} with {len(active_keys)} candidate models..."
                )

            # Subsample indices
            np.random.seed(random_seed + round_num)
            indices = np.random.choice(n_total, size=sample_size, replace=False)
            X_sub = X_train[indices]
            y_sub = y_train[indices]

            stage_scores = {}
            for key in active_keys:
                model_cfg = all_models[key]
                try:
                    m = model_cfg["class"](**model_cfg["params"])
                    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_seed) if is_classification else KFold(n_splits=cv_folds, shuffle=True, random_state=random_seed)
                    scorer = cls.CLASSIFICATION_SCORING.get(primary_metric, "f1_weighted") if is_classification else cls.REGRESSION_SCORING.get(primary_metric, "r2")
                    cv_res = cross_validate(m, X_sub, y_sub, cv=cv, scoring=scorer, error_score=0.0)
                    mean_score = float(np.mean(cv_res["test_score"]))
                    stage_scores[key] = mean_score
                except Exception as ex:
                    stage_scores[key] = -999.0

            # Sort active models by performance
            reverse = True if primary_metric not in ("mae", "mse", "rmse") else False
            sorted_candidates = sorted(active_keys, key=lambda k: stage_scores.get(k, -999), reverse=reverse)

            # Determine survivors
            if round_num < len(stages):
                # Keep top half (at least 1)
                keep_count = max(1, len(sorted_candidates) // 2) if len(sorted_candidates) > 2 else max(1, len(sorted_candidates) - 1)
                survivors = sorted_candidates[:keep_count]
                eliminated = sorted_candidates[keep_count:]
            else:
                survivors = sorted_candidates
                eliminated = []

            time_elapsed = round(time.time() - start_overall_time, 2)
            elimination_log.append({
                "round": round_num,
                "stage_name": stage["name"],
                "sample_fraction": fraction,
                "sample_size": sample_size,
                "active_models": [all_models[k]["display_name"] for k in active_keys],
                "scores": {all_models[k]["display_name"]: round(stage_scores.get(k, 0), 4) for k in active_keys},
                "survivors": [all_models[k]["display_name"] for k in survivors],
                "eliminated": [all_models[k]["display_name"] for k in eliminated],
                "time_elapsed_seconds": time_elapsed
            })

            survival_funnel.append({
                "stage": stage["name"],
                "models_evaluated": len(active_keys),
                "models_survived": len(survivors),
                "time_elapsed_s": time_elapsed
            })

            last_stage_scores = stage_scores
            active_keys = survivors

            # Check time budget
            if time.time() - start_overall_time > budget_seconds:
                break

        # Final fit on full training data for all evaluated models (for leaderboard consistency)
        leaderboard = []
        for rank, key in enumerate(active_keys):
            model_cfg = all_models[key]
            m = model_cfg["class"](**model_cfg["params"])
            m.fit(X_train, y_train)
            final_trained_models[key] = m

            leaderboard.append({
                "algorithm": key,
                "display_name": model_cfg["display_name"],
                "metrics": {primary_metric: round(last_stage_scores.get(key, 0.0), 4)},
                "cv_scores": {},
                "primary_metric_value": round(last_stage_scores.get(key, 0.0), 4),
                "training_duration": round(time.time() - start_overall_time, 2),
                "hyperparameters": model_cfg["params"],
                "status": "completed",
                "rank": rank + 1,
                "survived_successive_halving": True
            })

        # Also add eliminated models into leaderboard marked as eliminated
        for round_info in elimination_log:
            for elim_name in round_info["eliminated"]:
                # find key
                matching_key = next((k for k, v in all_models.items() if v["display_name"] == elim_name), None)
                if matching_key and not any(e["algorithm"] == matching_key for e in leaderboard):
                    leaderboard.append({
                        "algorithm": matching_key,
                        "display_name": elim_name,
                        "metrics": {primary_metric: round(round_info["scores"].get(elim_name, 0.0), 4)},
                        "cv_scores": {},
                        "primary_metric_value": round(round_info["scores"].get(elim_name, 0.0), 4),
                        "training_duration": round_info["time_elapsed_seconds"],
                        "hyperparameters": all_models[matching_key]["params"],
                        "status": "eliminated",
                        "rank": len(leaderboard) + 1,
                        "eliminated_in_round": round_info["round"],
                        "survived_successive_halving": False
                    })

        if progress_callback:
            progress_callback(progress=100, message="Budget AutoML completed.")

        return {
            "leaderboard": leaderboard,
            "trained_models": final_trained_models,
            "primary_metric": primary_metric,
            "task_type": task_type,
            "cv_folds": cv_folds,
            "random_seed": random_seed,
            "elimination_log": elimination_log,
            "survival_funnel": survival_funnel,
            "budget_seconds": budget_seconds,
            "total_duration": round(time.time() - start_overall_time, 2)
        }

    @staticmethod
    def save_model(model: Any, save_dir: str, model_name: str) -> str:
        """Save a trained model to disk using joblib."""
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f"{model_name}.joblib")
        joblib.dump(model, path)
        return path

    @staticmethod
    def load_model(path: str) -> Any:
        """Load a saved model from disk."""
        return joblib.load(path)
