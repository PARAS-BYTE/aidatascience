from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    bio: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    role: str
    avatar: str
    bio: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    title: str
    details: Optional[str] = None
    created_at: datetime


class UserStats(BaseModel):
    datasets_count: int = 0
    total_storage_bytes: int = 0
    models_count: int = 0
    experiments_count: int = 0
    jobs_count: int = 0
    best_accuracy: Optional[float] = None


class UserProfileSummaryResponse(BaseModel):
    user: UserResponse
    stats: UserStats
    uploaded_datasets: List[Dict[str, Any]] = []
    trained_models: List[Dict[str, Any]] = []
    recent_activities: List[UserActivityResponse] = []
