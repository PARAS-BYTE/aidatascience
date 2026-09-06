"""
Multi-Agent REST & Streaming Endpoints — Parallel DAG, Blackboard, and Power BI Dashboard APIs.
"""
import json
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User, Dataset
from app.api.deps import get_current_user
from app.services.multi_agent.orchestrator import MultiAgentOrchestrator
from app.services.multi_agent.blackboard import get_blackboard, clear_blackboard, sanitize_for_json
from app.services.multi_agent.agents.analysis_agents import WhyInvestigationAgent
from app.services.multi_agent.agents.dashboard_agents import DashboardUpdateAgent


router = APIRouter(prefix="/multi-agent", tags=["Multi-Agent Data Scientist"])


class MultiAgentChatRequest(BaseModel):
    message: str = Field(..., description="Natural language prompt for the agent team")
    session_id: str = Field(..., description="Unique conversation session ID")
    dataset_id: str = Field(..., description="Target dataset ID")
    target: Optional[str] = Field(None, description="Optional target column for ML tasks")


class WhyInvestigationRequest(BaseModel):
    session_id: str
    dataset_id: str
    metric: Optional[str] = None
    dimension: Optional[str] = None


class DashboardPatchRequest(BaseModel):
    session_id: str
    dataset_id: str
    prompt: str


def _get_accessible_dataset(db: Session, dataset_id: str, current_user: User) -> Dataset:
    sample_names = ["customer_churn.csv", "house_prices.csv"]
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        (Dataset.user_id == current_user.id) | 
        (Dataset.original_filename.in_(sample_names)) |
        (current_user.role == "admin")
    ).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return dataset


@router.post("/chat")
async def run_multi_agent_chat(
    request: MultiAgentChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Execute the multi-agent parallel pipeline synchronously and return full blackboard & report.
    """
    dataset = _get_accessible_dataset(db, request.dataset_id, current_user)

    try:
        result = await MultiAgentOrchestrator.run_pipeline(
            db=db,
            session_id=request.session_id,
            dataset_id=request.dataset_id,
            prompt=request.message,
            target_col=request.target,
        )
        return sanitize_for_json(result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-agent execution error: {str(e)}",
        )


@router.get("/stream")
async def stream_multi_agent_events(
    session_id: str = Query(...),
    dataset_id: str = Query(...),
    prompt: str = Query(""),
    target: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Server-Sent Events (SSE) live stream yielding DAG execution events,
    agent progress, and incremental dashboard cards.
    """
    dataset = _get_accessible_dataset(db, dataset_id, current_user)

    async def event_generator():
        try:
            async for event in MultiAgentOrchestrator.stream_pipeline(
                db=db,
                session_id=session_id,
                dataset_id=dataset_id,
                prompt=prompt,
                target_col=target,
            ):
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
        except Exception as e:
            err_payload = json.dumps({"event": "error", "message": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/why-investigation")
async def run_why_investigation(
    request: WhyInvestigationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Direct parallel root-cause dimension decomposition.
    """
    dataset = _get_accessible_dataset(db, request.dataset_id, current_user)

    blackboard = get_blackboard(session_id=request.session_id, dataset_id=request.dataset_id)
    MultiAgentOrchestrator.load_dataset_to_blackboard(db=db, dataset_id=request.dataset_id, blackboard=blackboard)
    
    result = WhyInvestigationAgent.run(
        blackboard=blackboard,
        metric=request.metric,
        dimension_to_decompose=request.dimension,
    )
    return {
        "session_id": request.session_id,
        "dataset_id": request.dataset_id,
        "why_analysis": result,
    }


@router.post("/dashboard/patch")
async def patch_dashboard_spec(
    request: DashboardPatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Incrementally modify and patch the active dashboard spec with natural language.
    """
    dataset = _get_accessible_dataset(db, request.dataset_id, current_user)

    blackboard = get_blackboard(session_id=request.session_id, dataset_id=request.dataset_id)
    MultiAgentOrchestrator.load_dataset_to_blackboard(db=db, dataset_id=request.dataset_id, blackboard=blackboard)
    
    updated_spec = DashboardUpdateAgent.run(blackboard=blackboard, prompt=request.prompt)
    return {
        "session_id": request.session_id,
        "dataset_id": request.dataset_id,
        "dashboard_spec": updated_spec,
    }


@router.get("/blackboard/{session_id}")
def get_blackboard_state(
    session_id: str,
    dataset_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Inspect the shared blackboard memory store for an active session.
    """
    blackboard = get_blackboard(session_id=session_id, dataset_id=dataset_id)
    return blackboard.snapshot()


@router.delete("/blackboard/{session_id}")
def reset_blackboard(
    session_id: str,
    dataset_id: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Reset and clear blackboard cache for a session.
    """
    clear_blackboard(session_id=session_id, dataset_id=dataset_id)
    return {"status": "cleared", "session_id": session_id}


# ─── A5 & B8: Timeline & Human-in-the-Loop Review Gate ─────────────────────────

class EventReviewRequest(BaseModel):
    status: str  # approved, rejected, edited
    edited_payload: Optional[Dict[str, Any]] = None


@router.get("/runs/{run_id}/timeline")
def get_run_timeline(run_id: str, db: Session = Depends(get_db)):
    """Retrieve chronological audit timeline of blackboard events for a run."""
    from app.services.multi_agent.blackboard import SharedBlackboard
    events = SharedBlackboard.get_timeline(run_id, db)
    return {"run_id": run_id, "events": events, "count": len(events)}


@router.patch("/runs/{run_id}/events/{event_id}")
def review_run_event(run_id: str, event_id: str, request: EventReviewRequest, db: Session = Depends(get_db)):
    """Approve, reject, or edit a blackboard event / review gate."""
    from app.services.multi_agent.blackboard import SharedBlackboard
    try:
        updated = SharedBlackboard.review_event(event_id, request.status, request.edited_payload, db)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─── B9: Plugin Marketplace ───────────────────────────────────────────────────

class PluginToggleRequest(BaseModel):
    is_enabled: bool


@router.get("/plugins")
def list_agent_plugins(db: Session = Depends(get_db)):
    """List all available custom agent plugins in the marketplace."""
    from app.services.multi_agent.plugin_registry import PluginRegistry
    plugins = PluginRegistry.list_plugins(db)
    return {"plugins": plugins, "total": len(plugins)}


@router.patch("/plugins/{plugin_id}")
def toggle_agent_plugin(plugin_id: str, request: PluginToggleRequest, db: Session = Depends(get_db)):
    """Toggle a plugin enabled or disabled."""
    from app.services.multi_agent.plugin_registry import PluginRegistry
    try:
        res = PluginRegistry.toggle_plugin(plugin_id, request.is_enabled, db)
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
