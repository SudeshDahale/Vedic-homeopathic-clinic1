from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException
from datetime import datetime, timedelta

from app.models.user import User
from app.models.clinic import Clinic

from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    CreateStaffRequest
)

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token
)

from app.enums import (
    UserRole,
    SubscriptionPlan,
    SubscriptionStatus
)

import uuid
import pytz

IST = pytz.timezone("Asia/Kolkata")


# =========================================================
# Signup Clinic + Doctor
# =========================================================
def signup_clinic(db: Session, data: SignupRequest) -> dict:
    """
    Create clinic + doctor account together.
    Only doctors can self-signup.
    Receptionists are created by doctor.
    """

    # Check duplicate user
    existing = db.query(User).filter(
        or_(
            User.email == data.email,
            User.phone == data.phone
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email or phone already registered. Please login."
        )

    # Create clinic
    clinic_id = str(uuid.uuid4())

    trial_end = datetime.now(IST) + timedelta(days=30)

    clinic = Clinic(
        id=clinic_id,
        name=data.clinic_name,
        doctor_name=data.doctor_name,
        qualification=data.qualification,
        city=data.city,
        phone=data.phone,
        email=data.email,
        timings=data.timings,

        # Subscription
        plan_id=SubscriptionPlan.STARTER.value,
        subscription_status=SubscriptionStatus.TRIAL.value,
        trial_end_date=trial_end,
        staff_limit=2,

        # Branding defaults
        branding_enabled=False,
        primary_color="#16a34a",
        secondary_color="#2563eb",
        is_active=True
    )

    db.add(clinic)

    # Create doctor user
    user = User(
        clinic_id=clinic_id,
        name=data.doctor_name,
        phone=data.phone,
        email=data.email,

        # SECURE PASSWORD
        hashed_password=hash_password(data.password),

        role=UserRole.DOCTOR
    )

    db.add(user)

    db.commit()
    db.refresh(user)

    # JWT token
    token = create_access_token({
        "user_id": user.id,
        "clinic_id": clinic_id,
        "role": UserRole.DOCTOR.value,
        "name": data.doctor_name,
        "clinic_name": data.clinic_name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": UserRole.DOCTOR.value,
        "name": data.doctor_name,
        "clinic_id": clinic_id,
        "clinic_name": data.clinic_name,
        "user_id": user.id,
        "plan": SubscriptionPlan.STARTER.value,
        "message": "Clinic account created successfully. 30-day trial activated."
    }


# =========================================================
# Login User
# =========================================================
def login_user(db: Session, data: LoginRequest) -> dict:
    """
    Login using email OR phone.
    """

    user = db.query(User).filter(
        or_(
            User.email == data.login,
            User.phone == data.login
        )
    ).first()

    # Verify password
    if not user or not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email/phone or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="Account deactivated. Contact clinic admin."
        )

    # Get clinic
    clinic = db.query(Clinic).filter(
        Clinic.id == user.clinic_id
    ).first()

    clinic_name = clinic.name if clinic else "Clinic"

    # FIXED PLAN LOGIC
    plan = (
        clinic.plan_id
        if clinic and clinic.plan_id
        else SubscriptionPlan.STARTER.value
    )

    # Branding
    branding = None

    if clinic and getattr(clinic, "branding_enabled", False):
        branding = {
            "primary_color": clinic.primary_color,
            "secondary_color": clinic.secondary_color,
            "custom_logo": clinic.custom_logo
        }

    # JWT
    token = create_access_token({
        "user_id": user.id,
        "clinic_id": user.clinic_id,
        "role": user.role.value,
        "name": user.name,
        "clinic_name": clinic_name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "name": user.name,
        "clinic_id": user.clinic_id,
        "clinic_name": clinic_name,
        "user_id": user.id,
        "plan": plan,
        "branding": branding
    }


# =========================================================
# Create Staff Account
# =========================================================
def create_staff_account(
    db: Session,
    data: CreateStaffRequest,
    clinic_id: str
) -> User:
    """
    Doctor creates receptionist/staff accounts.
    """

    # Get clinic
    clinic = db.query(Clinic).filter(
        Clinic.id == clinic_id
    ).first()

    # Current staff count
    current_staff = db.query(User).filter(
        User.clinic_id == clinic_id,
        User.role != UserRole.DOCTOR,
        User.is_active == True
    ).count()

    # Staff limit check
    if clinic and current_staff >= (clinic.staff_limit or 2):
        raise HTTPException(
            status_code=403,
            detail=f"Staff limit reached ({clinic.staff_limit}). Upgrade your plan."
        )

    # Duplicate check
    existing = db.query(User).filter(
        or_(
            User.phone == data.phone,
            User.email == data.email
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email or phone already registered."
        )

    # Create staff user
    user = User(
        clinic_id=clinic_id,
        name=data.name,
        phone=data.phone,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role
    )

    db.add(user)

    db.commit()
    db.refresh(user)

    return user