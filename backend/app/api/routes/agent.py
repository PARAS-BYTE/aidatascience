from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.core.config import settings
from app.db.database import get_db
from app.db.models import User, Dataset
from app.api.deps import get_current_user, get_optional_user
from app.schemas.dataset import AgentChatRequest, AgentChatResponse, AutoPilotRequest, AutoPilotResponse
from app.services.agent_service import AIAgent
from app.services.prompt_guard_service import PromptGuardService

router = APIRouter(prefix="/agent", tags=["AI Agent"])

@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Send a message to the AI Data Scientist with Prompt Guard protection."""
    if request.dataset_id and current_user:
        dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id, Dataset.user_id == current_user.id).first()
        if not dataset:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    result = AIAgent.process_message(
        db=db,
        message=request.message,
        session_id=request.session_id,
        dataset_id=request.dataset_id,
        guard_model=request.guard_model,
        llm_model=request.llm_model,
    )
    return result


@router.post("/auto-pilot", response_model=AutoPilotResponse)
def run_auto_pilot(
    request: AutoPilotRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute the autonomous AI data science pipeline:
    1. Intelligence & Target Identification
    2. AI Feature Engineering Strategy Formulation
    3. Automated Cleaning & Data Transformation
    4. AI Model Selection Reasoning
    5. AutoML Training with Cross-Validation
    6. Leaderboard & SHAP Explainability Diagnostics
    """
    dataset = db.query(Dataset).filter(Dataset.id == request.dataset_id, Dataset.user_id == current_user.id).first()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    return AIAgent.run_auto_pilot_pipeline(
        db=db,
        dataset_id=request.dataset_id,
        target=request.target,
        llm_model=request.llm_model,
        enable_feature_engineering=request.enable_feature_engineering,
        cv_folds=request.cv_folds,
        max_interactions=request.max_interactions,
    )


@router.get("/models")
def get_agent_models() -> Dict[str, Any]:
    """Get available Groq LLM models and Prompt Guard models."""
    return {
        "active_chat_model": settings.GROQ_CHAT_MODEL,
        "active_guard_model": settings.GROQ_PROMPT_GUARD_MODEL,
        "prompt_guard_enabled": settings.PROMPT_GUARD_ENABLED,
        "prompt_guard_threshold": settings.PROMPT_GUARD_THRESHOLD,
        "supported_guard_models": PromptGuardService.SUPPORTED_MODELS,
        "supported_chat_models": [
            {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B (Groq)"},
            {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B (Groq)"},
            {"id": "qwen/qwen3.8-27b", "name": "Qwen 3.8 27B (Groq)"},
            {"id": "groq/compound", "name": "Groq Compound"},
        ],
        "has_api_key": bool(settings.GROQ_API_KEY or settings.LLM_API_KEY),
    }


# ─── B1: Ask Your Data (Text-to-SQL) ──────────────────────────────────────────

from pydantic import BaseModel
from fastapi import HTTPException, status
from app.services.text2sql_service import Text2SQLService


class AskDataRequest(BaseModel):
    dataset_id: str
    question: str


@router.post("/ask-data")
def ask_data(request: AskDataRequest, db: Session = Depends(get_db)):
    """Convert natural language into SQL, execute against DuckDB, and return chart data."""
    try:
        result = Text2SQLService.ask_data(request.dataset_id, request.question, db)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Query error: {str(e)}")
