"""
Authentication API endpoints.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.core.security import verify_password, create_access_token, get_current_user
from app.core.config import ACCESS_TOKEN_EXPIRE_MINUTES
from app.utils.logger import api_logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """Login request body."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response body."""
    success: bool
    token: str = None
    data: dict = None
    error: str = None


class UserResponse(BaseModel):
    """Current user response."""
    username: str
    name: str
    role: str


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token.
    
    Frontend integration point: POST /api/auth/login
    """
    api_logger.info(f"Login attempt for user: {request.username}")
    
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.hashed_password):
        api_logger.warning(f"Failed login attempt for user: {request.username}")
        return LoginResponse(
            success=False,
            error="Invalid username or password"
        )
    
    if not user.is_active:
        api_logger.warning(f"Login attempt for inactive user: {request.username}")
        return LoginResponse(
            success=False,
            error="Account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(
        data={
            "sub": user.username,
            "role": user.role,
            "name": user.name,
            "user_id": user.id
        },
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    api_logger.info(f"Successful login for user: {request.username}")
    
    return LoginResponse(
        success=True,
        token=access_token,
        data={
            "name": user.name,
            "role": user.role,
            "username": user.username
        }
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        username=current_user["username"],
        name=current_user["name"],
        role=current_user["role"]
    )
