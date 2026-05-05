from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.visit import (
    VisitCreate, VitalsInput, AllopathyInput,
    HomeopathyInput, CloseVisitInput
)
from app.services import visit_service
from app.middleware.auth_middleware import (
    get_current_user, doctor_only, receptionist_or_doctor
)
from app.models.user import User

router = APIRouter(prefix="/visits", tags=["Visits"])


@router.post("/")
def create_visit(
    data:         VisitCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Start new visit.
    Receptionist creates it when patient sits down.
    Fee is optional here — entered at close time.
    """
    return visit_service.create_visit(
        db, data, current_user.clinic_id, current_user.id
    )


@router.put("/{visit_id}/vitals")
def save_vitals(
    visit_id:     str,
    data:         VitalsInput,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Record BP, weight, height before consultation.
    Both receptionist and doctor can record vitals.
    """
    return visit_service.save_vitals(
        db, visit_id, current_user.clinic_id, data
    )


@router.post("/{visit_id}/allopathy")
def save_allopathy(
    visit_id:     str,
    data:         AllopathyInput,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """
    Save prescription — DOCTOR ONLY.
    Receptionist cannot view or edit prescription.
    """
    return visit_service.save_allopathy_rx(
        db, visit_id, current_user.clinic_id, data
    )


@router.post("/{visit_id}/homeopathy")
def save_homeopathy(
    visit_id:     str,
    data:         HomeopathyInput,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """
    Save homeopathy case sheet — DOCTOR ONLY.
    Remedy and potency are clinical decisions.
    Receptionist never sees this data.
    """
    return visit_service.save_homeopathy_case(
        db, visit_id, current_user.clinic_id, data
    )


@router.put("/{visit_id}/close")
def close_visit(
    visit_id:     str,
    data:         CloseVisitInput,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Close visit and collect payment.
    Fee MUST be entered manually — no fixed fee for any visit type.
    Automatically schedules follow-up reminders after closing.
    """
    return visit_service.close_visit(
        db, visit_id, current_user.clinic_id, data
    )


@router.get("/{visit_id}")
def get_visit(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """Get complete visit with vitals, prescription or case sheet"""
    return visit_service.get_visit(
        db, visit_id, current_user.clinic_id
    )