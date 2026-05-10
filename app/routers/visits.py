from fastapi import APIRouter, Depends

from fastapi.responses import Response

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

from app.services.visit_service import (
    get_consultation_schema
)

from app.services.pdf_service import (
    generate_prescription_pdf
)

from app.middleware.auth_middleware import (
    get_current_user,
    doctor_only,
    receptionist_or_doctor
)

from app.models.user import User

from app.models.clinic import Clinic

from app.models.visit import Visit

from app.models.patient import Patient


router = APIRouter(
    prefix="/visits",
    tags=["Visits"]
)


# =====================================================
# CONSULTATION SCHEMA
# =====================================================

@router.get("/consultation-schema")
def consultation_schema(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):
    """
    Returns dynamic consultation fields
    based on clinic type.
    """

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    clinic_type = (
        clinic.clinic_type
        if clinic else "ALLOPATHY"
    )

    return {

        "clinic_type":
            clinic_type,

        "fields":
            get_consultation_schema(
                clinic_type
            )
    }


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
    Save vitals.
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
    Doctor-only prescription.
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
    Doctor-only homeopathy case.
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
    Close visit + payment.
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
    Consultation wizard progress.
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
    Update wizard step.
    """

    return visit_service.update_visit_status(

        db,

        visit_id,

        current_user.clinic_id,

        status
    )


# =====================================================
# GENERATE PRESCRIPTION PDF
# =====================================================

@router.get("/{visit_id}/pdf")
def get_prescription_pdf(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    )
):
    """
    Generate printable prescription PDF.
    """

    # -------------------------------------------------
    # GET VISIT
    # -------------------------------------------------

    visit = db.query(Visit).filter(

        Visit.id == visit_id,

        Visit.clinic_id == current_user.clinic_id

    ).first()

    if not visit:

        return Response(

            content="Visit not found",

            status_code=404
        )

    # -------------------------------------------------
    # GET PATIENT
    # -------------------------------------------------

    patient = db.query(Patient).filter(
        Patient.id == visit.patient_id
    ).first()

    # -------------------------------------------------
    # GET CLINIC
    # -------------------------------------------------

    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()

    # -------------------------------------------------
    # GENERATE PDF
    # -------------------------------------------------

    pdf_bytes = generate_prescription_pdf(

        visit = visit.__dict__,

        clinic = clinic.__dict__ if clinic else {},

        doctor = current_user.__dict__,

        patient = patient.__dict__ if patient else {}
    )

    # -------------------------------------------------
    # RETURN INLINE PDF
    # -------------------------------------------------

    return Response(

        content = pdf_bytes,

        media_type = "application/pdf",

        headers = {

            "Content-Disposition":
                f"inline; "
                f"filename=rx_{visit_id[:8]}.pdf"
        }
    )