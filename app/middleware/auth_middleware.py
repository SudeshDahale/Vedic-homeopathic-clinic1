from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.security import decode_token
from app.models.user import User, UserRole

# This tells FastAPI to look for "Bearer <token>" in request headers
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    WHY: Every protected endpoint uses this.
    Reads token → finds user → returns user object.
    If token missing or invalid → returns 401 error automatically.
    """
    token   = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again."
        )

    user = db.query(User).filter(User.id == payload.get("user_id")).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )

    return user

def doctor_only(current_user: User = Depends(get_current_user)) -> User:
    """
    WHY: Analytics, revenue, full patient history = DOCTOR only.
    Receptionist trying to access → gets 403 Forbidden immediately.
    """
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Doctor role required."
        )
    return current_user

def receptionist_or_doctor(current_user: User = Depends(get_current_user)) -> User:
    """Both roles can access — used for patient entry, queue, payments"""
    return current_user