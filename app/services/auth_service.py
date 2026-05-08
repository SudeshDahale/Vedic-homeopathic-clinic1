# =====================================================
# FILE: app/services/auth_service.py
# =====================================================

from sqlalchemy.orm import Session
from sqlalchemy import or_

from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.clinic import Clinic

from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    SignupRequest
)

from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token
)

import uuid


# =====================================================
# REGISTER RECEPTIONIST / STAFF
# =====================================================
def register_user(
    db: Session,
    data: RegisterRequest
) -> User:

    existing = db.query(User).filter(
        User.phone == data.phone
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered"
        )

    existing_email = None

    if data.email:
        existing_email = db.query(User).filter(
            User.email == data.email
        ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user = User(
        clinic_id=data.clinic_id,
        name=data.name,
        phone=data.phone,
        email=data.email,

        # IMPORTANT
        hashed_password=hash_password(data.password),

        role=(
            UserRole.DOCTOR
            if data.role == "DOCTOR"
            else UserRole.RECEPTIONIST
        ),

        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# =====================================================
# PUBLIC CLINIC SIGNUP
# =====================================================
def signup_clinic(
    db: Session,
    data: SignupRequest
) -> dict:

    # Check email
    existing_email = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    # Check phone
    existing_phone = db.query(User).filter(
        User.phone == data.phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Phone already registered"
        )

    # Create clinic
    clinic_id = str(uuid.uuid4())

    clinic = Clinic(
        id=clinic_id,
        name=data.clinic_name,
        doctor_name=data.doctor_name,
        qualification=data.qualification,
        city=data.city,
        phone=data.phone,
        email=data.email,
        timings=data.timings
    )

    db.add(clinic)

    # Create doctor user
    user = User(
        clinic_id=clinic_id,
        name=data.doctor_name,
        phone=data.phone,
        email=data.email,

        # IMPORTANT
        hashed_password=hash_password(data.password),

        role=UserRole.DOCTOR,
        is_active=True
    )

    db.add(user)

    db.commit()
    db.refresh(user)

    # Create token
    token = create_access_token({
        "user_id": str(user.id),
        "clinic_id": clinic_id,
        "role": user.role.value,
        "name": user.name,
        "clinic_name": data.clinic_name
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "name": user.name,
        "clinic_id": clinic_id,
        "clinic_name": data.clinic_name,
        "user_id": str(user.id),
        "message": "Account created successfully"
    }


# =====================================================
# LOGIN
# =====================================================
def login_user(
    db: Session,
    data: LoginRequest
) -> dict:

    # Login with phone OR email
    user = db.query(User).filter(
        or_(
            User.phone == data.login,
            User.email == data.login
        )
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password"
        )

    # Verify password
    if not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/phone or password"
        )

    # Active check
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Get clinic
    clinic = db.query(Clinic).filter(
        Clinic.id == user.clinic_id
    ).first()

    # Create JWT
    token = create_access_token({
        "user_id": str(user.id),
        "clinic_id": user.clinic_id,
        "role": user.role.value,
        "name": user.name,
        "clinic_name": clinic.name if clinic else ""
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role.value,
        "name": user.name,
        "clinic_id": user.clinic_id,
        "clinic_name": clinic.name if clinic else "",
        "user_id": str(user.id)
    }


# =====================================================
# GET USER
# =====================================================
def get_user_by_id(
    db: Session,
    user_id: str
) -> User:

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user