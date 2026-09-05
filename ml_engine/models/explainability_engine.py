"""
Explainability Engine — SHAP-based model explanations.
Uses TreeExplainer for tree models, fallback to KernelExplainer.
Never fabricates feature importance — all values from actual SHAP computation.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


class ExplainabilityEngine:
    """Generate real SHAP-based explanations for trained models."""

    @staticmethod
    def compute_global_importance(
        model: Any,
        X_sample: np.ndarray,
        feature_names: List[str],
        max_samples: int = 500,
    ) -> Dict[str, Any]:
        """
        Compute global feature importance using SHAP.
        Returns sorted feature importances from actual computation.
        """
        import shap

        # Subsample if dataset is large
        if len(X_sample) > max_samples:
            indices = np.random.choice(len(X_sample), max_samples, replace=False)
            X_subset = X_sample[indices]
        else:
            X_subset = X_sample

        try:
            # Try TreeExplainer first (fast, exact for tree models)
            if hasattr(model, "feature_importances_") or type(model).__name__ in (
                "XGBClassifier", "XGBRegressor",
                "RandomForestClassifier", "RandomForestRegressor",
                "GradientBoostingClassifier", "GradientBoostingRegressor",
            ):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(X_subset)
            else:
                # Fallback: KernelExplainer (slow but universal)
                bg = shap.kmeans(X_subset, min(10, len(X_subset)))
                explainer = shap.KernelExplainer(model.predict, bg)
                shap_values = explainer.shap_values(X_subset, nsamples=100)

            # Handle multi-class SHAP values
            if isinstance(shap_values, list):
                # Average absolute SHAP values across classes
                shap_abs = np.mean([np.abs(sv) for sv in shap_values], axis=0)
            else:
                shap_abs = np.abs(shap_values)

            # Mean absolute SHAP value per feature
            mean_importance = np.mean(shap_abs, axis=0)

            # Map to feature names (handle potential mismatch)
            n_features = min(len(feature_names), len(mean_importance))
            importance_dict = {}
            for i in range(n_features):
                importance_dict[feature_names[i]] = round(float(mean_importance[i]), 6)

            # Sort by importance
            sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

            return {
                "feature_importance": [
                    {"feature": name, "importance": score}
                    for name, score in sorted_features
                ],
                "top_features": [name for name, _ in sorted_features[:10]],
                "method": "shap",
                "n_samples_used": len(X_subset),
                "status": "success",
            }

        except Exception as e:
            # Fallback to model-based feature importance if available
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
                n_features = min(len(feature_names), len(importances))
                importance_dict = {
                    feature_names[i]: round(float(importances[i]), 6)
                    for i in range(n_features)
                }
                sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
                return {
                    "feature_importance": [
                        {"feature": name, "importance": score}
                        for name, score in sorted_features
                    ],
                    "top_features": [name for name, _ in sorted_features[:10]],
                    "method": "model_native",
                    "n_samples_used": 0,
                    "status": "fallback",
                    "warning": f"SHAP computation failed ({str(e)}). Using model-native feature importance.",
                }

            if hasattr(model, "coef_"):
                coefs = np.abs(model.coef_)
                if coefs.ndim > 1:
                    coefs = np.mean(coefs, axis=0)
                n_features = min(len(feature_names), len(coefs))
                importance_dict = {
                    feature_names[i]: round(float(coefs[i]), 6)
                    for i in range(n_features)
                }
                sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)
                return {
                    "feature_importance": [
                        {"feature": name, "importance": score}
                        for name, score in sorted_features
                    ],
                    "top_features": [name for name, _ in sorted_features[:10]],
                    "method": "coefficients",
                    "n_samples_used": 0,
                    "status": "fallback",
                    "warning": f"SHAP failed ({str(e)}). Using model coefficients.",
                }

            return {
                "feature_importance": [],
                "top_features": [],
                "method": "none",
                "n_samples_used": 0,
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    def explain_prediction(
        model: Any,
        instance: np.ndarray,
        feature_names: List[str],
        X_background: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Explain a single prediction using SHAP values.
        Returns per-feature contributions.
        """
        import shap

        instance = instance.reshape(1, -1) if instance.ndim == 1 else instance

        try:
            # Try TreeExplainer
            if hasattr(model, "feature_importances_") or type(model).__name__ in (
                "XGBClassifier", "XGBRegressor",
                "RandomForestClassifier", "RandomForestRegressor",
            ):
                explainer = shap.TreeExplainer(model)
                shap_values = explainer.shap_values(instance)
                base_value = explainer.expected_value
            else:
                if X_background is None or len(X_background) == 0:
                    return {"error": "Background data required for KernelExplainer", "status": "error"}
                bg = shap.kmeans(X_background, min(10, len(X_background)))
                explainer = shap.KernelExplainer(model.predict, bg)
                shap_values = explainer.shap_values(instance, nsamples=100)
                base_value = explainer.expected_value

            # Handle multi-class
            if isinstance(shap_values, list):
                # For binary, take positive class
                sv = shap_values[1] if len(shap_values) == 2 else shap_values[0]
                if isinstance(base_value, (list, np.ndarray)):
                    bv = base_value[1] if len(base_value) == 2 else base_value[0]
                else:
                    bv = base_value
            else:
                sv = shap_values
                bv = base_value

            sv_flat = sv.flatten()
            n_features = min(len(feature_names), len(sv_flat))

            contributions = []
            for i in range(n_features):
                contributions.append({
                    "feature": feature_names[i],
                    "value": round(float(instance[0, i]), 4) if i < instance.shape[1] else None,
                    "shap_value": round(float(sv_flat[i]), 6),
                    "direction": "positive" if sv_flat[i] > 0 else "negative",
                })

            # Sort by absolute SHAP value
            contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

            # Get prediction
            prediction = model.predict(instance)[0]
            probability = None
            if hasattr(model, "predict_proba"):
                try:
                    proba = model.predict_proba(instance)[0]
                    probability = round(float(max(proba)), 4)
                except Exception:
                    pass

            return {
                "prediction": str(prediction) if not isinstance(prediction, (int, float)) else round(float(prediction), 4),
                "probability": probability,
                "base_value": round(float(bv), 4) if not isinstance(bv, np.ndarray) else round(float(bv.item()), 4),
                "contributions": contributions,
                "top_positive": [c for c in contributions if c["direction"] == "positive"][:5],
                "top_negative": [c for c in contributions if c["direction"] == "negative"][:5],
                "status": "success",
            }

        except Exception as e:
            return {
                "error": str(e),
                "status": "error",
            }
