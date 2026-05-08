# =====================================================
# FILE: app/routers/auth.py
# =====================================================

from fastapi import (
    APIRouter,
    Depends
)

from sqlalchemy.orm import Session

from app.database import get_db

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    SignupRequest
)

from app.services.auth_service import (
    register_user,
    login_user,
    signup_clinic
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# =====================================================
# SIGNUP
# =====================================================
@router.post("/signup")
def signup(
    data: SignupRequest,
    db: Session = Depends(get_db)
):
    return signup_clinic(db, data)


# =====================================================
# LOGIN
# =====================================================
@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    return login_user(db, data)


# =====================================================
# REGISTER STAFF
# =====================================================
@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    user = register_user(db, data)

    return {
        "id": str(user.id),
        "name": user.name,
        "phone": user.phone,
        "email": user.email,
        "role": user.role.value,
        "clinic_id": user.clinic_id,
        "is_active": user.is_active
    }