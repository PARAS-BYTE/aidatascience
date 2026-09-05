from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User
from app.core.security import create_access_token
from app.api.deps import get_current_user
from app.schemas.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    UserUpdateRequest,
    UserResponse,
    TokenResponse,
    UserProfileSummaryResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & User Profile"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account and obtain access token."""
    user = AuthService.register_user(db, req)
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password and obtain access token."""
    user = AuthService.authenticate_user(db, req.email, req.password)
    token = create_access_token({"sub": user.id, "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get("/profile", response_model=UserProfileSummaryResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get comprehensive user profile with stats, uploaded datasets, trained models, and activity timeline."""
    summary = AuthService.get_user_profile_summary(db, current_user.id)
    return summary


@router.put("/profile", response_model=UserResponse)
def update_profile(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile details (name, bio, avatar)."""
    updated_user = AuthService.update_user_profile(db, current_user.id, req)
    AuthService.log_activity(
        db=db,
        user_id=current_user.id,
        action="PROFILE_UPDATED",
        title="Profile updated",
        details=f"Updated profile settings: name={updated_user.name}",
    )
    return UserResponse.model_validate(updated_user)
