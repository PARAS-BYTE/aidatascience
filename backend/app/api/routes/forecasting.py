"""
Forecasting API Route — Time-series projection and anomaly endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.api.deps import get_current_user
from app.services.forecasting_service import ForecastingService
from app.core.logging import logger

router = APIRouter(tags=["Forecasting"])


class ForecastRequest(BaseModel):
    date_column: Optional[str] = None
    value_column: Optional[str] = None
    horizon: int = Field(default=14, ge=1, le=90)


@router.post("/datasets/{dataset_id}/forecast")
def forecast_dataset(
    dataset_id: str,
    request: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate time-series projections, confidence intervals, trend decomposition,
    and historical anomaly flags for a temporal dataset.
    """
    try:
        return ForecastingService.run_forecast(
            db=db,
            dataset_id=dataset_id,
            user_id=current_user.id,
            date_column=request.date_column,
            value_column=request.value_column,
            horizon=request.horizon,
        )
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.error(f"Forecasting failed for {dataset_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Forecasting failed: {str(e)}",
        )
