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

security = HTTPBearer()


# =====================================================
# GET CURRENT USER
# =====================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Auth middleware.

    Reads JWT →
    validates token →
    validates user →
    validates clinic →
    returns authenticated user.
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

    # -------------------------------------------------
    # CLINIC VALIDATION
    # -------------------------------------------------

    if not user.clinic_id:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not assigned to any clinic"
        )

    clinic = db.query(Clinic).filter(
        Clinic.id == user.clinic_id
    ).first()

    if not clinic:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic not found"
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

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic not found"
        )

    # -------------------------------------------------
    # TRIAL EXPIRY CHECK
    # -------------------------------------------------

    if (

        clinic.subscription_status
        == SubscriptionStatus.TRIAL

        and clinic.trial_end_date
    ):

        # ---------------------------------------------
        # HANDLE NAIVE DATETIME SAFELY
        # ---------------------------------------------

        trial_end = (

            IST.localize(clinic.trial_end_date)

            if clinic.trial_end_date.tzinfo is None

            else clinic.trial_end_date
        )

        # ---------------------------------------------
        # CHECK EXPIRY
        # ---------------------------------------------

        if datetime.now(IST) > trial_end:

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
    Doctor-only endpoints.

    Receptionists blocked.
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
    """

    if current_user.role not in [
        UserRole.DOCTOR,
        UserRole.RECEPTIONIST
    ]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return current_user