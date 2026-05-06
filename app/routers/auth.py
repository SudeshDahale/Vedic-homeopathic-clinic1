from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import timedelta

from app.database import get_db
from app.models.user import User
from app.models.clinic import Clinic

from app.middleware.auth_middleware import (
    doctor_only,
    get_current_user
)

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.config import settings

# ─────────────────────────────────────────────────────
# Router
# ─────────────────────────────────────────────────────
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# ─────────────────────────────────────────────────────
# Request Schemas
# ─────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    name: str
    phone: str
    password: str
    role: str
    clinic_id: str


class LoginRequest(BaseModel):
    phone: str
    password: str


class ClinicSetup(BaseModel):
    name: str
    doctor_name: str
    qualification: Optional[str] = "B.H.M.S."
    address: Optional[str] = None
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    timings: Optional[str] = None
    logo_url: Optional[str] = None


# ─────────────────────────────────────────────────────
# Register
# ─────────────────────────────────────────────────────
@router.post("/register")
def register_user(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):

    existing = db.query(User).filter(
        User.phone == data.phone
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    user = User(
        name=data.name,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=data.role,  # OWNER / RECEPTIONIST
        clinic_id=data.clinic_id,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "id": user.id,
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
        "clinic_id": user.clinic_id,
        "is_active": user.is_active
    }


# ─────────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────────
@router.post("/login")
def login_user(
    data: LoginRequest,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.phone == data.phone
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid phone or password"
        )

    if not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid phone or password"
        )

    access_token = create_access_token(
        data={
            "user_id": str(user.id),
            "clinic_id": user.clinic_id,
            "role": user.role,
            "name": user.name
        },
        expires_delta=timedelta(
            minutes=settings.JWT_EXPIRE_MINUTES
        )
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "name": user.name,
            "role": user.role,
            "clinic_id": user.clinic_id
        }
    }


# ─────────────────────────────────────────────────────
# Clinic Setup
# ─────────────────────────────────────────────────────
@router.post("/clinic/setup")
def setup_clinic(
    data: ClinicSetup,
    db: Session = Depends(get_db),
    current_user: User = Depends(doctor_only)
):
    """
    One-time clinic setup.
    This data appears on receipts automatically.
    """

    existing = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    # ── Update existing clinic ───────────────────────
    if existing:

        existing.name = data.name
        existing.doctor_name = data.doctor_name
        existing.qualification = data.qualification
        existing.address = data.address
        existing.city = data.city
        existing.phone = data.phone
        existing.email = data.email
        existing.timings = data.timings
        existing.logo_url = data.logo_url

        db.commit()
        db.refresh(existing)

        return {
            "message": "Clinic updated",
            "clinic_id": existing.id
        }

    # ── Create new clinic ────────────────────────────
    clinic = Clinic(
        id=current_user.clinic_id,
        name=data.name,
        doctor_name=data.doctor_name,
        qualification=data.qualification,
        address=data.address,
        city=data.city,
        phone=data.phone,
        email=data.email,
        timings=data.timings,
        logo_url=data.logo_url
    )

    db.add(clinic)
    db.commit()
    db.refresh(clinic)

    return {
        "message": "Clinic created",
        "clinic_id": clinic.id
    }


# ─────────────────────────────────────────────────────
# Get Clinic
# ─────────────────────────────────────────────────────
@router.get("/clinic")
def get_clinic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    if not clinic:
        return {
            "message": "Clinic not set up yet"
        }

    return clinic