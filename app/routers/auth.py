from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, LoginResponse, UserResponse
from app.services import auth_service
from app.middleware.auth_middleware import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create Doctor or Receptionist account.
    First user created should be DOCTOR (clinic owner).
    """
    user = auth_service.register_user(db, data)
    return user

@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with phone + password.
    Returns JWT token — frontend stores this and sends with every request.
    Role in response tells frontend what UI to show.
    """
    return auth_service.login_user(db, data)

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current logged-in user info.
    Lovable frontend calls this on app load to check who is logged in.
    """
    return current_user