"""
Experiment Memory Service — Indexes experiments and retrieves similar past runs
with best hyperparameters and architecture choices.
"""
import json
import math
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.db.models import Experiment, ExperimentEmbedding, Dataset
from app.core.logging import logger


class ExperimentMemoryService:
    @staticmethod
    def _compute_embedding(text: str, dim: int = 64) -> List[float]:
        """
        Deterministic lightweight hashing vectorizer for zero-dependency local embeddings.
        """
        vec = np.zeros(dim, dtype=float)
        words = text.lower().replace("-", " ").replace("_", " ").split()
        if not words:
            return vec.tolist()

        for word in words:
            h = hash(word) % dim
            vec[h] += 1.0

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    @staticmethod
    def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        a = np.array(v1)
        b = np.array(v2)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    @classmethod
    def index_experiment(cls, db: Session, experiment_id: str) -> Optional[ExperimentEmbedding]:
        """
        Create and persist a semantic summary and embedding for a completed experiment.
        """
        try:
            exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
            if not exp:
                return None

            dataset = db.query(Dataset).filter(Dataset.id == exp.dataset_id).first()
            ds_name = dataset.original_filename if dataset else "unknown"

            summary = (
                f"Dataset: {ds_name}. Task: {exp.task_type}. Target: {exp.target_column}. "
                f"Metric: {exp.primary_metric}. Best Model: {exp.model_name}. "
                f"Validation Score: {exp.val_score:.4f}. "
                f"Config: {exp.hyperparameters or '{}'}."
            )

            fingerprint = f"{ds_name}_{exp.task_type}_{exp.target_column}"
            embedding_vec = cls._compute_embedding(summary)

            existing = db.query(ExperimentEmbedding).filter(
                ExperimentEmbedding.experiment_id == experiment_id
            ).first()

            if existing:
                existing.summary_text = summary
                existing.embedding_json = json.dumps(embedding_vec)
                existing.dataset_fingerprint = fingerprint
                db.commit()
                db.refresh(existing)
                return existing

            new_mem = ExperimentEmbedding(
                experiment_id=experiment_id,
                dataset_fingerprint=fingerprint,
                summary_text=summary,
                embedding_json=json.dumps(embedding_vec),
            )
            db.add(new_mem)
            db.commit()
            db.refresh(new_mem)
            return new_mem
        except Exception as e:
            logger.error(f"Failed to index experiment memory for {experiment_id}: {e}", exc_info=True)
            db.rollback()
            return None

    @classmethod
    def find_similar(cls, db: Session, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve nearest past experiment solutions based on semantic similarity.
        """
        query_vec = cls._compute_embedding(query)
        memories = db.query(ExperimentEmbedding).all()

        ranked = []
        for mem in memories:
            try:
                emb = json.loads(mem.embedding_json)
                score = cls._cosine_similarity(query_vec, emb)
                exp = db.query(Experiment).filter(Experiment.id == mem.experiment_id).first()
                if exp:
                    ranked.append({
                        "experiment_id": mem.experiment_id,
                        "similarity_score": round(score, 3),
                        "model_name": exp.model_name,
                        "task_type": exp.task_type,
                        "primary_metric": exp.primary_metric,
                        "val_score": exp.val_score,
                        "summary": mem.summary_text,
                        "created_at": exp.created_at.isoformat() if exp.created_at else None,
                    })
            except Exception:
                continue

        ranked.sort(key=lambda x: x["similarity_score"], reverse=True)
        return ranked[:top_k]
