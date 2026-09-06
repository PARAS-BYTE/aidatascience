"""
Shared Blackboard — Central results and state store for all agents.
Enables parallel agents to share insights, re-use cached computations, and persist cross-turn context.
"""
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import pandas as pd
import numpy as np


def sanitize_for_json(obj: Any) -> Any:
    """Recursively convert NumPy/Pandas scalar types into standard Python types for clean JSON serialization."""
    if obj is None:
        return None
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    if isinstance(obj, (int, np.integer)):
        return int(obj)
    if isinstance(obj, (float, np.floating)):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0
        return float(obj)
    if isinstance(obj, (np.ndarray, pd.Series)):
        return [sanitize_for_json(v) for v in obj.tolist()]
    if isinstance(obj, pd.DataFrame):
        return [sanitize_for_json(row) for row in obj.to_dict(orient="records")]
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(v) for v in obj]
    return obj


class SharedBlackboard:
    """
    In-memory results store keyed by (session_id, dataset_id).
    Maintains all intermediate data, agent contributions, critic validations, and logs.
    """

    def __init__(self, session_id: str, dataset_id: Optional[str] = None):
        self.session_id: str = session_id
        self.dataset_id: Optional[str] = dataset_id
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self._store: Dict[str, Any] = {}
        self._df_cache: Optional[pd.DataFrame] = None
        self._agent_logs: List[Dict[str, Any]] = []
        self._critic_logs: List[Dict[str, Any]] = []

    def set_df(self, df: pd.DataFrame) -> None:
        """Cache the active working dataframe."""
        self._df_cache = df
        self.updated_at = time.time()

    def get_df(self) -> Optional[pd.DataFrame]:
        """Retrieve the cached dataframe."""
        return self._df_cache

    def _persist_event(self, agent_name: str, event_type: str, payload: Any, status: str = "approved") -> None:
        """Persist blackboard event to database for audit timeline."""
        try:
            from app.db.database import SessionLocal
            from app.db.models import BlackboardEvent
            db = SessionLocal()
            try:
                event = BlackboardEvent(
                    run_id=self.session_id,
                    agent_name=agent_name,
                    event_type=event_type,
                    status=status,
                    payload=json.dumps(sanitize_for_json(payload)) if payload is not None else None
                )
                db.add(event)
                db.commit()
            finally:
                db.close()
        except Exception:
            pass

    def set(self, key: str, value: Any, agent_name: Optional[str] = None) -> None:
        """Store a sanitized value on the blackboard with optional agent attribution."""
        if isinstance(value, (pd.DataFrame, np.ndarray)):
            clean_value = value
        else:
            clean_value = sanitize_for_json(value)
        self._store[key] = {
            "value": clean_value,
            "agent": agent_name,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "timestamp": time.time(),
        }
        self.updated_at = time.time()
        if agent_name:
            self._agent_logs.append({
                "agent": agent_name,
                "action": f"write_blackboard:{key}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            self._persist_event(agent_name=agent_name, event_type="write", payload={"key": key, "preview": str(clean_value)[:300]})

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve the raw stored value for a given key."""
        entry = self._store.get(key)
        if entry is None:
            return default
        return entry.get("value", default)

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve the full wrapper metadata for a key."""
        return self._store.get(key)

    def has(self, key: str) -> bool:
        """Check if a key exists on the blackboard."""
        return key in self._store

    def delete(self, key: str) -> None:
        """Remove a key from the blackboard."""
        if key in self._store:
            del self._store[key]
            self.updated_at = time.time()

    def log_agent_activity(self, agent_name: str, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Record an agent activity log."""
        log_entry = {
            "agent": agent_name,
            "action": action,
            "details": sanitize_for_json(details) or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._agent_logs.append(log_entry)
        self._persist_event(agent_name=agent_name, event_type="activity", payload=log_entry)

    def log_critic_review(self, agent_name: str, passed: bool, score: float, comments: str, corrections: Optional[Dict[str, Any]] = None) -> None:
        """Record a validation decision made by the Critic Agent."""
        review_entry = {
            "target_agent": agent_name,
            "passed": bool(passed),
            "score": float(score),
            "comments": str(comments),
            "corrections": sanitize_for_json(corrections),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._critic_logs.append(review_entry)
        self._persist_event(agent_name="CriticAgent", event_type="critic_review", payload=review_entry)

    @classmethod
    def get_timeline(cls, run_id: str, db: Any) -> List[Dict[str, Any]]:
        """Retrieve chronological persisted timeline of blackboard events for a run."""
        from app.db.models import BlackboardEvent
        events = db.query(BlackboardEvent).filter(
            BlackboardEvent.run_id == run_id
        ).order_by(BlackboardEvent.created_at.asc()).all()

        return [
            {
                "id": ev.id,
                "run_id": ev.run_id,
                "agent_name": ev.agent_name,
                "event_type": ev.event_type,
                "status": ev.status,
                "payload": json.loads(ev.payload) if ev.payload else {},
                "created_at": ev.created_at.isoformat() if ev.created_at else None
            }
            for ev in events
        ]

    @classmethod
    def review_event(cls, event_id: str, status: str, edited_payload: Optional[Dict[str, Any]], db: Any) -> Dict[str, Any]:
        """Update review gate status on a blackboard event."""
        from app.db.models import BlackboardEvent
        event = db.query(BlackboardEvent).filter(BlackboardEvent.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")

        event.status = status
        if edited_payload is not None:
            event.payload = json.dumps(edited_payload)
        db.commit()
        db.refresh(event)

        return {
            "id": event.id,
            "run_id": event.run_id,
            "agent_name": event.agent_name,
            "status": event.status,
            "payload": json.loads(event.payload) if event.payload else {}
        }

    def get_critic_logs(self) -> List[Dict[str, Any]]:
        return list(self._critic_logs)

    def get_agent_logs(self) -> List[Dict[str, Any]]:
        return list(self._agent_logs)

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the entire blackboard state."""
        return sanitize_for_json({
            "session_id": self.session_id,
            "dataset_id": self.dataset_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "keys_present": list(self._store.keys()),
            "profile": self.get("profile"),
            "quality": self.get("quality"),
            "statistics": self.get("statistics"),
            "relationships": self.get("relationships"),
            "semantics": self.get("semantics"),
            "query_plan": self.get("query_plan"),
            "query_result": self.get("query_result"),
            "trends": self.get("trends"),
            "segments": self.get("segments"),
            "anomalies": self.get("anomalies"),
            "why_analysis": self.get("why_analysis"),
            "dashboard_spec": self.get("dashboard_spec"),
            "ml_task": self.get("ml_task"),
            "features": self.get("features"),
            "leaderboard": self.get("leaderboard"),
            "explainability": self.get("explainability"),
            "narrative": self.get("narrative"),
            "critic_reviews": self.get_critic_logs(),
            "agent_logs": self.get_agent_logs()[-30:],
        })


# Global in-memory cache of blackboards
_GLOBAL_BLACKBOARDS: Dict[str, SharedBlackboard] = {}


def get_blackboard(session_id: str, dataset_id: Optional[str] = None) -> SharedBlackboard:
    """Get or create a SharedBlackboard instance for a session."""
    key = f"{session_id}:{dataset_id or 'global'}"
    if key not in _GLOBAL_BLACKBOARDS:
        _GLOBAL_BLACKBOARDS[key] = SharedBlackboard(session_id=session_id, dataset_id=dataset_id)
    elif dataset_id and _GLOBAL_BLACKBOARDS[key].dataset_id != dataset_id:
        _GLOBAL_BLACKBOARDS[key].dataset_id = dataset_id
    return _GLOBAL_BLACKBOARDS[key]


def clear_blackboard(session_id: str, dataset_id: Optional[str] = None) -> None:
    """Clear blackboard for a session."""
    key = f"{session_id}:{dataset_id or 'global'}"
    if key in _GLOBAL_BLACKBOARDS:
        del _GLOBAL_BLACKBOARDS[key]
