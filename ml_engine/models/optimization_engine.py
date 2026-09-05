"""
Optimization Engine — Hyperparameter optimization using Optuna.
Supports configurable trials, timeout, and metric selection.
"""
import time
import numpy as np
from typing import Dict, Any, Optional, Callable
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold

import optuna
from optuna.exceptions import TrialPruned

from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from xgboost import XGBClassifier, XGBRegressor

# Suppress Optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)


class OptimizationEngine:
    """Optimize hyperparameters using Optuna with real cross-validation."""

    SEARCH_SPACES = {
        "xgboost_classification": {
            "model_class": XGBClassifier,
            "fixed_params": {"eval_metric": "logloss", "verbosity": 0},
            "params": {
                "learning_rate": ("float_log", 0.01, 0.3),
                "max_depth": ("int", 3, 10),
                "n_estimators": ("int", 50, 500),
                "subsample": ("float", 0.6, 1.0),
                "colsample_bytree": ("float", 0.6, 1.0),
                "min_child_weight": ("int", 1, 10),
                "gamma": ("float", 0.0, 5.0),
                "reg_alpha": ("float_log", 1e-8, 10.0),
                "reg_lambda": ("float_log", 1e-8, 10.0),
            },
        },
        "xgboost_regression": {
            "model_class": XGBRegressor,
            "fixed_params": {"verbosity": 0},
            "params": {
                "learning_rate": ("float_log", 0.01, 0.3),
                "max_depth": ("int", 3, 10),
                "n_estimators": ("int", 50, 500),
                "subsample": ("float", 0.6, 1.0),
                "colsample_bytree": ("float", 0.6, 1.0),
                "min_child_weight": ("int", 1, 10),
                "gamma": ("float", 0.0, 5.0),
                "reg_alpha": ("float_log", 1e-8, 10.0),
                "reg_lambda": ("float_log", 1e-8, 10.0),
            },
        },
        "random_forest_classification": {
            "model_class": RandomForestClassifier,
            "fixed_params": {},
            "params": {
                "n_estimators": ("int", 50, 500),
                "max_depth": ("int_or_none", 3, 30),
                "min_samples_split": ("int", 2, 20),
                "min_samples_leaf": ("int", 1, 10),
                "max_features": ("categorical", ["sqrt", "log2", None]),
            },
        },
        "random_forest_regression": {
            "model_class": RandomForestRegressor,
            "fixed_params": {},
            "params": {
                "n_estimators": ("int", 50, 500),
                "max_depth": ("int_or_none", 3, 30),
                "min_samples_split": ("int", 2, 20),
                "min_samples_leaf": ("int", 1, 10),
                "max_features": ("categorical", ["sqrt", "log2", None]),
            },
        },
        "logistic_regression": {
            "model_class": LogisticRegression,
            "fixed_params": {"max_iter": 1000},
            "params": {
                "C": ("float_log", 1e-4, 100.0),
                "penalty": ("categorical", ["l1", "l2"]),
                "solver": ("categorical", ["liblinear", "saga"]),
            },
        },
    }

    METRIC_MAPPING = {
        "accuracy": "accuracy",
        "precision": "precision_weighted",
        "recall": "recall_weighted",
        "f1": "f1_weighted",
        "roc_auc": "roc_auc_ovr_weighted",
        "mae": "neg_mean_absolute_error",
        "mse": "neg_mean_squared_error",
        "r2": "r2",
        "rmse": "neg_mean_squared_error",
    }

    @classmethod
    def _sample_params(cls, trial: optuna.Trial, param_space: Dict) -> Dict:
        """Sample hyperparameters from the search space."""
        params = {}
        for name, spec in param_space.items():
            ptype = spec[0]
            if ptype == "float":
                params[name] = trial.suggest_float(name, spec[1], spec[2])
            elif ptype == "float_log":
                params[name] = trial.suggest_float(name, spec[1], spec[2], log=True)
            elif ptype == "int":
                params[name] = trial.suggest_int(name, spec[1], spec[2])
            elif ptype == "int_or_none":
                use_none = trial.suggest_categorical(f"{name}_none", [True, False])
                if use_none:
                    params[name] = None
                else:
                    params[name] = trial.suggest_int(name, spec[1], spec[2])
            elif ptype == "categorical":
                params[name] = trial.suggest_categorical(name, spec[1])
        return params

    @classmethod
    def optimize(
        cls,
        X_train: np.ndarray,
        y_train: np.ndarray,
        algorithm: str,
        task_type: str,
        metric: str = "f1",
        n_trials: int = 50,
        timeout: int = 300,
        cv_folds: int = 5,
        random_seed: int = 42,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run Optuna optimization for a given algorithm.
        Returns optimization results with best params and trial history.
        """
        is_classification = "classification" in task_type

        # Determine search space key
        if algorithm == "xgboost":
            space_key = "xgboost_classification" if is_classification else "xgboost_regression"
        elif algorithm == "random_forest":
            space_key = "random_forest_classification" if is_classification else "random_forest_regression"
        elif algorithm == "logistic_regression":
            space_key = "logistic_regression"
        else:
            return {"error": f"Unsupported algorithm: {algorithm}"}

        if space_key not in cls.SEARCH_SPACES:
            return {"error": f"No search space defined for: {space_key}"}

        space_config = cls.SEARCH_SPACES[space_key]
        sklearn_metric = cls.METRIC_MAPPING.get(metric, metric)

        # Higher is better for most metrics; negate for MAE/MSE/RMSE
        direction = "minimize" if metric in ("mae", "mse", "rmse") else "maximize"

        # CV setup
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

        trial_history = []
        start_time = time.time()

        def objective(trial: optuna.Trial) -> float:
            sampled_params = cls._sample_params(trial, space_config["params"])
            all_params = {**space_config["fixed_params"], **sampled_params, "random_state": random_seed, "n_jobs": -1}

            # Handle solver compatibility for logistic regression
            if algorithm == "logistic_regression":
                if all_params.get("penalty") == "l1" and all_params.get("solver") not in ("liblinear", "saga"):
                    all_params["solver"] = "saga"

            try:
                model = space_config["model_class"](**all_params)
                scores = cross_val_score(model, X_train, y_train, cv=cv, scoring=sklearn_metric)
                score = float(np.mean(scores))

                trial_history.append({
                    "number": trial.number,
                    "value": round(score if not sklearn_metric.startswith("neg_") else -score, 4),
                    "params": sampled_params,
                    "status": "completed",
                })

                if progress_callback:
                    progress_callback(
                        progress=min(99, (trial.number + 1) / n_trials * 100),
                        message=f"Trial {trial.number + 1}/{n_trials} — Score: {score:.4f}",
                    )

                return score

            except Exception as e:
                trial_history.append({
                    "number": trial.number,
                    "value": None,
                    "params": sampled_params,
                    "status": "failed",
                    "error": str(e),
                })
                raise TrialPruned(str(e))

        study = optuna.create_study(direction=direction, sampler=optuna.samplers.TPESampler(seed=random_seed))
        study.optimize(objective, n_trials=n_trials, timeout=timeout, show_progress_bar=False)

        total_duration = round(time.time() - start_time, 2)

        # Get best params and train final model
        best_params = {**space_config["fixed_params"], **study.best_params, "random_state": random_seed, "n_jobs": -1}
        # Clean up _none params
        for key in list(best_params.keys()):
            if key.endswith("_none"):
                del best_params[key]

        best_model = space_config["model_class"](**best_params)
        best_model.fit(X_train, y_train)

        best_score = study.best_value
        if sklearn_metric.startswith("neg_"):
            best_score = -best_score

        if progress_callback:
            progress_callback(progress=100, message="Optimization complete.")

        return {
            "algorithm": algorithm,
            "best_score": round(float(best_score), 4),
            "best_params": study.best_params,
            "best_model": best_model,
            "n_trials_completed": len(study.trials),
            "n_trials_failed": sum(1 for t in trial_history if t["status"] == "failed"),
            "trial_history": trial_history,
            "metric": metric,
            "duration": total_duration,
            "timeout_reached": total_duration >= timeout,
        }
