from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database import get_db

from app.schemas.visit import (
    VisitCreate,
    VitalsInput,
    AllopathyInput,
    HomeopathyInput,
    CloseVisitInput
)

from app.services import visit_service

from app.middleware.auth_middleware import (
    get_current_user,
    doctor_only,
    receptionist_or_doctor
)

from app.models.user import User


router = APIRouter(
    prefix="/visits",
    tags=["Visits"]
)


# =====================================================
# CREATE VISIT
# =====================================================

@router.post("/")
def create_visit(
    data: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        receptionist_or_doctor
    )
):
    """
    Start new visit.

    Receptionist creates visit when
    patient arrives.

    Fee optional here —
    entered while closing visit.
    """

    return visit_service.create_visit(

        db,

        data,

        current_user.clinic_id,

        current_user.id
    )


# =====================================================
# SAVE VITALS
# =====================================================

@router.put("/{visit_id}/vitals")
def save_vitals(
    visit_id: str,
    data: VitalsInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        receptionist_or_doctor
    )
):
    """
    Save BP, weight, height etc.

    Receptionist and doctor both allowed.
    """

    return visit_service.save_vitals(

        db,

        visit_id,

        current_user.clinic_id,

        data
    )


# =====================================================
# SAVE ALLOPATHY RX
# =====================================================

@router.post("/{visit_id}/allopathy")
def save_allopathy(
    visit_id: str,
    data: AllopathyInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        doctor_only
    )
):
    """
    Doctor-only prescription entry.
    """

    return visit_service.save_allopathy_rx(

        db,

        visit_id,

        current_user.clinic_id,

        data
    )


# =====================================================
# SAVE HOMEOPATHY CASE
# =====================================================

@router.post("/{visit_id}/homeopathy")
def save_homeopathy(
    visit_id: str,
    data: HomeopathyInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        doctor_only
    )
):
    """
    Doctor-only homeopathy case sheet.
    """

    return visit_service.save_homeopathy_case(

        db,

        visit_id,

        current_user.clinic_id,

        data
    )


# =====================================================
# CLOSE VISIT
# =====================================================

@router.put("/{visit_id}/close")
def close_visit(
    visit_id: str,
    data: CloseVisitInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        receptionist_or_doctor
    )
):
    """
    Close visit + payment collection.

    Automatically schedules followups.
    """

    return visit_service.close_visit(

        db,

        visit_id,

        current_user.clinic_id,

        data
    )


# =====================================================
# GET VISIT
# =====================================================

@router.get("/{visit_id}")
def get_visit(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):
    """
    Complete visit details.
    """

    return visit_service.get_visit(

        db,

        visit_id,

        current_user.clinic_id
    )


# =====================================================
# GET WIZARD STATE
# =====================================================

@router.get("/{visit_id}/wizard")
def get_wizard_state(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):
    """
    Get current wizard progress.

    Frontend uses this to:
    - continue unfinished consultation
    - restore current step
    - show progress UI
    """

    return visit_service.get_visit_wizard_state(

        db,

        visit_id,

        current_user.clinic_id
    )


# =====================================================
# UPDATE VISIT STATUS
# =====================================================

@router.put("/{visit_id}/status")
def update_status(
    visit_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):
    """
    Move visit to next workflow stage.

    Example:
    DRAFT -> ACTIVE -> BILLING -> COMPLETED
    """

    return visit_service.update_visit_status(

        db,

        visit_id,

        current_user.clinic_id,

        status
    )