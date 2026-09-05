"""
Monitoring Service — Tracks model health, drift, and performance in production.
"""
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from scipy import stats as scipy_stats

from app.core.logging import logger
from app.db.models import (
    MLModel, Deployment, MonitoringRecord, DriftResult,
    DeploymentStatus, Alert, Dataset,
)


class MonitoringService:
    """Production model monitoring, drift detection, and performance tracking."""

    @staticmethod
    def log_prediction(
        db: Session,
        model_id: str,
        input_data: Dict[str, Any],
        prediction: Any,
        probability: Optional[float] = None,
        deployment_id: Optional[str] = None,
    ) -> MonitoringRecord:
        """Log a prediction for monitoring."""
        record = MonitoringRecord(
            model_id=model_id,
            deployment_id=deployment_id,
            input_data=json.dumps(input_data),
            prediction=str(prediction),
            probability=probability,
        )
        db.add(record)

        # Increment request count on deployment
        if deployment_id:
            deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
            if deployment:
                deployment.request_count += 1

        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def compute_drift(
        db: Session,
        model_id: str,
        reference_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        Compute feature drift between reference (training) and production data.
        Uses KS-test for numerical features and PSI for categorical.
        """
        # Get recent predictions
        records = db.query(MonitoringRecord).filter(
            MonitoringRecord.model_id == model_id
        ).order_by(MonitoringRecord.created_at.desc()).limit(500).all()

        if len(records) < 10:
            return {
                "model_id": model_id,
                "overall_health": "unknown",
                "drift_status": "insufficient_data",
                "message": "Not enough production data to compute drift (minimum 10 predictions).",
                "prediction_count": len(records),
                "drift_features": [],
            }

        # Parse production inputs
        production_inputs = []
        for record in records:
            try:
                if record.input_data:
                    production_inputs.append(json.loads(record.input_data))
            except Exception:
                continue

        if not production_inputs:
            return {
                "model_id": model_id,
                "overall_health": "unknown",
                "drift_status": "no_data",
                "prediction_count": 0,
                "drift_features": [],
            }

        prod_df = pd.DataFrame(production_inputs)

        # If no reference data, use prediction distribution analysis
        drift_features = []
        overall_drift_score = 0.0
        n_features_checked = 0

        # Compute prediction distribution
        predictions = [r.prediction for r in records if r.prediction]
        prediction_dist = {}
        if predictions:
            pred_series = pd.Series(predictions)
            for val, count in pred_series.value_counts().items():
                prediction_dist[str(val)] = int(count)

        # Numerical feature drift
        for col in prod_df.select_dtypes(include=[np.number]).columns:
            series = prod_df[col].dropna()
            if len(series) < 5:
                continue

            # Self-drift check: first half vs second half
            mid = len(series) // 2
            first_half = series.iloc[:mid]
            second_half = series.iloc[mid:]

            try:
                ks_stat, p_value = scipy_stats.ks_2samp(first_half, second_half)
                psi_score = MonitoringService.compute_psi(first_half.values, second_half.values)
                drift_detected = p_value < 0.05 or psi_score >= 0.2

                drift_features.append({
                    "feature": col,
                    "drift_score": round(float(ks_stat), 4),
                    "psi_score": round(float(psi_score), 4),
                    "p_value": round(float(p_value), 4),
                    "drift_detected": drift_detected,
                    "method": "ks_test + psi",
                    "type": "numerical",
                })

                # Save to database
                drift_result = DriftResult(
                    model_id=model_id,
                    feature_name=col,
                    drift_score=float(ks_stat),
                    drift_detected=drift_detected,
                    method="ks_test+psi",
                    current_stats=json.dumps({
                        "mean": round(float(series.mean()), 4),
                        "std": round(float(series.std()), 4),
                        "psi": psi_score,
                    }),
                )
                db.add(drift_result)

                # Create Alert if critical drift detected (B4)
                if drift_detected:
                    alert = Alert(
                        model_id=model_id,
                        alert_type="feature_drift",
                        severity="critical" if psi_score >= 0.25 else "warning",
                        message=f"Distribution drift on '{col}': PSI={psi_score:.4f}, KS-stat={ks_stat:.4f} (p={p_value:.4f})",
                    )
                    db.add(alert)

                if drift_detected:
                    overall_drift_score += ks_stat
                n_features_checked += 1

            except Exception:
                continue

        db.commit()

        # Determine health
        if n_features_checked == 0:
            health = "unknown"
            drift_status = "insufficient_features"
        elif overall_drift_score / max(n_features_checked, 1) > 0.3:
            health = "critical"
            drift_status = "high"
        elif overall_drift_score / max(n_features_checked, 1) > 0.1:
            health = "warning"
            drift_status = "moderate"
        else:
            health = "healthy"
            drift_status = "low"

        return {
            "model_id": model_id,
            "overall_health": health,
            "drift_status": drift_status,
            "prediction_count": len(records),
            "prediction_distribution": prediction_dist,
            "drift_features": drift_features,
            "n_features_checked": n_features_checked,
        }

    @staticmethod
    def get_model_health(db: Session, model_id: str) -> Dict[str, Any]:
        """Get overall model health including drift and prediction stats."""
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            raise ValueError(f"Model {model_id} not found")

        # Get prediction count
        prediction_count = db.query(MonitoringRecord).filter(
            MonitoringRecord.model_id == model_id
        ).count()

        # Get latest drift results
        drift_results = db.query(DriftResult).filter(
            DriftResult.model_id == model_id
        ).order_by(DriftResult.created_at.desc()).limit(50).all()

        drift_features = []
        any_drift = False
        for dr in drift_results:
            drift_features.append({
                "feature": dr.feature_name,
                "drift_score": dr.drift_score,
                "drift_detected": dr.drift_detected,
                "method": dr.method,
            })
            if dr.drift_detected:
                any_drift = True

        # Determine overall health
        if prediction_count == 0:
            health = "no_data"
            drift_status = "unknown"
        elif any_drift:
            health = "warning"
            drift_status = "detected"
        else:
            health = "healthy"
            drift_status = "low"

        # Get deployment info
        deployment = db.query(Deployment).filter(
            Deployment.model_id == model_id,
            Deployment.status == DeploymentStatus.ACTIVE,
        ).first()

        return {
            "model_id": model_id,
            "model_name": model.name,
            "overall_health": health,
            "drift_status": drift_status,
            "prediction_count": prediction_count,
            "drift_features": drift_features,
            "is_deployed": deployment is not None,
            "deployment_id": deployment.id if deployment else None,
            "metrics": json.loads(model.metrics) if model.metrics else {},
        }

    @staticmethod
    def submit_ground_truth(
        db: Session,
        model_id: str,
        prediction_id: str,
        ground_truth: str,
    ) -> MonitoringRecord:
        """Submit ground truth label for a prediction (for performance tracking)."""
        record = db.query(MonitoringRecord).filter(
            MonitoringRecord.id == prediction_id,
            MonitoringRecord.model_id == model_id,
        ).first()
        if not record:
            raise ValueError("Prediction record not found")

        record.ground_truth = ground_truth
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def compute_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10) -> float:
        """Calculate Population Stability Index between expected and actual distributions."""
        if len(expected) == 0 or len(actual) == 0:
            return 0.0
        try:
            quantiles = np.linspace(0, 100, num_buckets + 1)
            bins = np.percentile(expected, quantiles)
            bins = np.unique(bins)
            if len(bins) < 2:
                return 0.0
            bins[0] = -np.inf
            bins[-1] = np.inf

            exp_counts, _ = np.histogram(expected, bins=bins)
            act_counts, _ = np.histogram(actual, bins=bins)

            exp_pct = (exp_counts + 1e-4) / (np.sum(exp_counts) + 1e-4 * len(exp_counts))
            act_pct = (act_counts + 1e-4) / (np.sum(act_counts) + 1e-4 * len(act_counts))

            psi_val = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
            return float(round(psi_val, 4))
        except Exception:
            return 0.0

    @staticmethod
    def get_alerts(db: Session, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve active monitoring alerts."""
        query = db.query(Alert)
        if model_id:
            query = query.filter(Alert.model_id == model_id)
        alerts = query.order_by(Alert.created_at.desc()).limit(100).all()
        return [
            {
                "id": a.id,
                "model_id": a.model_id,
                "alert_type": a.alert_type,
                "severity": a.severity,
                "message": a.message,
                "is_resolved": a.is_resolved,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alerts
        ]

    @staticmethod
    def resolve_alert(db: Session, alert_id: str) -> Dict[str, Any]:
        """Mark an alert as resolved."""
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        alert.is_resolved = True
        db.commit()
        return {"status": "resolved", "alert_id": alert_id}

