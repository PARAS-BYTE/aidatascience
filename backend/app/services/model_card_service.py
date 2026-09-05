"""
Model Card Service — Auto-generates standardized, production-grade Model Cards
documenting model architecture, performance, training data, and ethical considerations.
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import MLModel, Experiment, Dataset, ModelCard

logger = logging.getLogger(__name__)


class ModelCardService:
    @staticmethod
    def generate_card(model_id: str, db: Session) -> str:
        """Generate or update the comprehensive Markdown model card for a given ML model."""
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        exp = db.query(Experiment).filter(Experiment.id == model.experiment_id).first()
        dataset = db.query(Dataset).filter(Dataset.id == model.dataset_id).first()

        metrics = json.loads(model.metrics) if model.metrics else {}
        hyperparams = json.loads(model.hyperparameters) if model.hyperparameters else {}
        feature_names = json.loads(model.feature_names) if model.feature_names else []

        # Explainability check
        shap_summary = "Not computed yet."
        if model.explainability_data:
            try:
                shap_data = json.loads(model.explainability_data)
                top_features = shap_data.get("feature_importance", [])[:5]
                if top_features:
                    shap_summary = "\n".join([f"- **{f.get('feature')}**: importance score {round(f.get('importance', 0), 4)}" for f in top_features])
            except Exception:
                pass

        # Metrics rows
        metrics_table_rows = "\n".join([f"| {k} | {round(v, 4) if isinstance(v, (int, float)) else v} |" for k, v in metrics.items()])
        if not metrics_table_rows:
            metrics_table_rows = "| Primary Metric | N/A |"

        # Hyperparameters rows
        hyperparams_table_rows = "\n".join([f"| `{k}` | `{v}` |" for k, v in hyperparams.items()])
        if not hyperparams_table_rows:
            hyperparams_table_rows = "| Standard Default | Default |"

        dataset_name = dataset.original_filename if dataset else "Internal Dataset"
        task_str = model.task_type.value if hasattr(model.task_type, "value") else str(model.task_type)

        md = f"""# Model Card: {model.name} (v{model.version})

## 1. Model Overview
- **Model Identifier:** `{model.id}`
- **Algorithm:** `{model.algorithm}`
- **Task Type:** `{task_str}`
- **Target Feature:** `{model.target_column}`
- **Current Lifecycle Status:** `{model.status.value if hasattr(model.status, 'value') else model.status}`
- **Created Date:** {model.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if model.created_at else 'N/A'}

---

## 2. Intended Use
- **Primary Use Case:** Automated predictive inference on tabular data for `{model.target_column}`.
- **Intended Users:** Data Scientists, ML Engineers, and downstream API consumers.
- **Out-of-Scope Uses:** Real-time life-critical systems without human oversight; input data exceeding the recorded domain distribution.

---

## 3. Training & Preprocessing
- **Source Dataset:** `{dataset_name}`
- **Total Features Used:** {len(feature_names)}
- **Feature Set:** `{', '.join(feature_names[:10])}{'...' if len(feature_names) > 10 else ''}`
- **Train / Test Ratio:** {f"{(1 - exp.train_test_split) * 100:.0f}% train / {exp.train_test_split * 100:.0f}% test" if exp else "80% train / 20% test"}
- **Random Seed:** {exp.random_seed if exp else 42}

---

## 4. Quantitative Evaluation & Metrics
| Metric | Value |
|---|---|
{metrics_table_rows}

---

## 5. Hyperparameter Configuration
| Parameter | Setting |
|---|---|
{hyperparams_table_rows}

---

## 6. Interpretability & Top Features (SHAP)
{shap_summary}

---

## 7. Ethical Considerations, Caveats & Limitations
- **Data Drift Sensitivity:** The model relies on the feature distributions recorded at training time. Drift monitoring (PSI / KS-test) is strongly recommended.
- **Handling of Missing Data:** Automatic median imputation for continuous features and mode imputation for categorical features.
- **Edge Cases:** Inputs with unseen categorical levels will be encoded as zero-vectors via one-hot encoder fallback.
"""

        # Persist or update in DB
        existing_card = db.query(ModelCard).filter(ModelCard.model_id == model_id).first()
        if existing_card:
            existing_card.content_md = md
            existing_card.generated_at = datetime.now(timezone.utc)
        else:
            new_card = ModelCard(
                model_id=model_id,
                content_md=md,
                generated_at=datetime.now(timezone.utc)
            )
            db.add(new_card)

        db.commit()
        return md

    @classmethod
    def get_card(cls, model_id: str, db: Session) -> str:
        """Fetch existing model card or auto-generate if missing."""
        card = db.query(ModelCard).filter(ModelCard.model_id == model_id).first()
        if card:
            return card.content_md
        return cls.generate_card(model_id, db)
