from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from sqlalchemy.orm import Session

from datetime import datetime

import pytz

from app.database import get_db

from app.utils.security import decode_token

from app.models.user import (
    User,
    UserRole
)

from app.models.clinic import Clinic

from app.enums import SubscriptionStatus


# =====================================================
# TIMEZONE
# =====================================================

IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# JWT SECURITY
# =====================================================

# FastAPI automatically looks for:
# Authorization: Bearer <token>

security = HTTPBearer()


# =====================================================
# GET CURRENT USER
# =====================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Every protected endpoint uses this.

    Reads token →
    finds user →
    returns user object.

    If token invalid/missing →
    returns 401 automatically.
    """

    token = credentials.credentials

    payload = decode_token(token)

    # -------------------------------------------------
    # INVALID TOKEN
    # -------------------------------------------------

    if not payload:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Invalid or expired token. "
                "Please login again."
            )
        )

    # -------------------------------------------------
    # FIND USER
    # -------------------------------------------------

    user = db.query(User).filter(
        User.id == payload.get("user_id")
    ).first()

    # -------------------------------------------------
    # USER VALIDATION
    # -------------------------------------------------

    if not user or not user.is_active:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated"
        )

    return user


# =====================================================
# SUBSCRIPTION CHECK
# =====================================================

def check_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Check if clinic subscription is active.

    Blocks access if:
    - trial expired
    - inactive subscription
    """

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    # -------------------------------------------------
    # SAFETY CHECK
    # -------------------------------------------------

    if not clinic:
        return current_user

    # -------------------------------------------------
    # TRIAL EXPIRY CHECK
    # -------------------------------------------------

    if (

        clinic.subscription_status
        == SubscriptionStatus.TRIAL

        and clinic.trial_end_date

        and datetime.now(IST)
        > clinic.trial_end_date.replace(
            tzinfo=IST
        )
    ):

        raise HTTPException(

            status_code=402,

            detail={

                "message":
                    "Trial expired. "
                    "Please upgrade to continue.",

                "code":
                    "TRIAL_EXPIRED",

                "upgrade_url":
                    "/settings/subscription"
            }
        )

    return current_user


# =====================================================
# DOCTOR ONLY
# =====================================================

def doctor_only(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Doctor-only endpoints:

    - Analytics
    - Revenue
    - Reports
    - Full patient history

    Receptionists receive:
    403 Forbidden
    """

    if current_user.role != UserRole.DOCTOR:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied. "
                "Doctor role required."
            )
        )

    return current_user


# =====================================================
# RECEPTIONIST OR DOCTOR
# =====================================================

def receptionist_or_doctor(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Both doctor + receptionist allowed.

    Used for:
    - patient entry
    - queue
    - billing
    - payments
    """

    return current_user