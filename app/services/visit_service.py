import json

from datetime import datetime

from sqlalchemy.orm import Session

from fastapi import HTTPException, status

from app.models.visit import (
    Visit,
    VisitType,
    PaymentStatus,
    PaymentMode,
    AllopathyRx,
    HomeopathyCase,
    Vitals
)

from app.models.billing import Payment

from app.schemas.visit import (
    VisitCreate,
    VitalsInput,
    AllopathyInput,
    HomeopathyInput,
    CloseVisitInput
)

from app.services.growth_service import (
    schedule_followups,
    update_patient_stats
)

import pytz


IST = pytz.timezone("Asia/Kolkata")


# =====================================================
# DYNAMIC CONSULTATION SCHEMA
# =====================================================

CLINIC_FIELDS = {

    # -------------------------------------------------
    # HOMEOPATHY
    # -------------------------------------------------

    "HOMEOPATHY": [

        "chief_complaint",

        "miasm",

        "constitution",

        "mental_generals",

        "physical_generals",

        "modalities",

        "remedy",

        "potency",

        "dose"
    ],

    # -------------------------------------------------
    # ALLOPATHY
    # -------------------------------------------------

    "ALLOPATHY": [

        "chief_complaint",

        "history",

        "examination",

        "diagnosis",

        "icd_code",

        "rx",

        "advice",

        "follow_up_days"
    ],

    # -------------------------------------------------
    # AYURVEDIC
    # -------------------------------------------------

    "AYURVEDIC": [

        "chief_complaint",

        "prakriti",

        "dosha",

        "nadi",

        "remedy",

        "anupaan",

        "pathya_apathya"
    ],
}


# =====================================================
# GET CONSULTATION SCHEMA
# =====================================================

def get_consultation_schema(
    clinic_type: str
) -> list:
    """
    Returns consultation fields dynamically
    based on clinic type.
    """

    return CLINIC_FIELDS.get(

        clinic_type.upper(),

        CLINIC_FIELDS["ALLOPATHY"]
    )


# =====================================================
# CREATE VISIT
# =====================================================

def create_visit(
    db: Session,
    data: VisitCreate,
    clinic_id: str,
    doctor_id: str
) -> Visit:
    """
    Start new visit.

    Fee optional here.
    Receptionist enters final fee while closing.
    """

    visit = Visit(

        clinic_id = clinic_id,

        patient_id = data.patient_id,

        doctor_id = doctor_id,

        type = (
            VisitType.ALLOPATHY
            if data.type == "ALLOPATHY"
            else VisitType.HOMEOPATHY
        ),

        # -------------------------------------------------
        # WIZARD FLOW STATUS
        # -------------------------------------------------

        visit_status = "DRAFT",

        chief_complaint = data.chief_complaint,

        disease_type = (
            data.disease_type or "default"
        ),

        fee = data.fee or 0,

        notes = data.notes,

        episode_id = data.episode_id,

        visit_date = datetime.now(IST)
    )

    db.add(visit)

    db.commit()

    db.refresh(visit)

    return visit


# =====================================================
# SAVE VITALS
# =====================================================

def save_vitals(
    db: Session,
    visit_id: str,
    clinic_id: str,
    data: VitalsInput
) -> dict:
    """
    Save patient vitals.
    """

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    vitals = visit.vitals

    if not vitals:

        vitals = Vitals(
            visit_id=visit_id
        )

        db.add(vitals)

    vitals.weight_kg = data.weight_kg

    vitals.height_cm = data.height_cm

    vitals.bp_systolic = data.bp_systolic

    vitals.bp_diastolic = data.bp_diastolic

    vitals.temperature = data.temperature

    vitals.pulse_rate = data.pulse_rate

    db.commit()

    return {

        "message":
            "Vitals saved",

        "weight_kg":
            data.weight_kg,

        "height_cm":
            data.height_cm,

        "bp":
            f"{data.bp_systolic}/"
            f"{data.bp_diastolic}",

        "temperature":
            data.temperature,

        "pulse_rate":
            data.pulse_rate
    }


# =====================================================
# SAVE ALLOPATHY RX
# =====================================================

def save_allopathy_rx(
    db: Session,
    visit_id: str,
    clinic_id: str,
    data: AllopathyInput
) -> dict:
    """
    Save allopathy prescription.
    """

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    rx = visit.allopathy_rx

    if not rx:

        rx = AllopathyRx(
            visit_id=visit_id
        )

        db.add(rx)

    rx.medicines = json.dumps([
        m.model_dump()
        for m in data.medicines
    ])

    rx.advice = data.advice

    rx.next_visit_date = (
        data.next_visit_date
    )

    db.commit()

    return {

        "message":
            "Prescription saved",

        "medicines_count":
            len(data.medicines),

        "advice":
            data.advice,

        "next_visit_date":
            str(data.next_visit_date or "")
    }


# =====================================================
# SAVE HOMEOPATHY CASE
# =====================================================

def save_homeopathy_case(
    db: Session,
    visit_id: str,
    clinic_id: str,
    data: HomeopathyInput
) -> dict:
    """
    Save complete homeopathy case.
    """

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    case = visit.homeopathy_case

    if not case:

        case = HomeopathyCase(
            visit_id=visit_id
        )

        db.add(case)

    case.chief_complaint = (
        data.chief_complaint
    )

    case.history_present = (
        data.history_present
    )

    case.history_past = (
        data.history_past
    )

    case.history_surgical = (
        data.history_surgical
    )

    case.history_family = (
        data.history_family
    )

    case.thermal_sensation = (
        data.thermal_sensation
    )

    case.appetite = data.appetite

    case.thirst = data.thirst

    case.sleep = data.sleep

    case.dreams = data.dreams

    case.menstrual = data.menstrual

    case.mind_symptoms = (
        data.mind_symptoms
    )

    case.particulars = json.dumps(
        data.particulars or {}
    )

    case.rubrics = json.dumps(

        [
            r.model_dump()
            for r in data.rubrics
        ]

        if data.rubrics else []
    )

    case.remedy = data.remedy

    case.potency = data.potency

    case.repetition = data.repetition

    case.miasm = data.miasm

    db.commit()

    return {

        "message":
            "Homeopathy case saved",

        "remedy":
            data.remedy,

        "potency":
            data.potency,

        "rubrics_count":
            (
                len(data.rubrics)
                if data.rubrics else 0
            )
    }


# =====================================================
# CLOSE VISIT
# =====================================================

def close_visit(
    db: Session,
    visit_id: str,
    clinic_id: str,
    data: CloseVisitInput
) -> dict:

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    if visit.closed_at:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit is already closed"
        )

    try:

        pay_mode = PaymentMode[
            data.payment_mode.upper()
        ]

    except KeyError:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid payment mode: "
                f"{data.payment_mode}"
            )
        )

    visit.fee = data.fee

    visit.disease_type = (
        data.disease_type
        or visit.disease_type
        or "default"
    )

    visit.payment_status = (
        PaymentStatus.PAID
    )

    visit.payment_mode = pay_mode

    visit.closed_at = datetime.now(IST)

    visit.visit_status = "COMPLETED"

    payment = Payment(

        visit_id = visit_id,

        amount = data.fee,

        mode = pay_mode
    )

    db.add(payment)

    db.commit()

    db.refresh(visit)

    update_patient_stats(
        db,
        visit.patient_id,
        float(data.fee)
    )

    followups = schedule_followups(

        db = db,

        visit_id = visit_id,

        patient_id = visit.patient_id,

        clinic_id = clinic_id,

        disease_type = (
            visit.disease_type
        ),

        channel = (
            data.followup_channel
            or "WHATSAPP"
        )
    )

    return {

        "status":
            "closed",

        "visit_id":
            visit_id,

        "amount_paid":
            float(data.fee),

        "payment_mode":
            data.payment_mode.upper(),

        "followups_scheduled":
            followups,

        "followups_count":
            len(followups),

        "message":
            (
                f"Visit closed. "
                f"{len(followups)} follow-up reminders scheduled."
            )
    }


# =====================================================
# UPDATE VISIT STATUS
# =====================================================

def update_visit_status(
    db: Session,
    visit_id: str,
    clinic_id: str,
    new_status: str
) -> dict:

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    visit.visit_status = new_status

    db.commit()

    return {

        "visit_id":
            visit_id,

        "status":
            new_status,

        "message":
            f"Visit moved to {new_status}"
    }


# =====================================================
# GET VISIT WIZARD STATE
# =====================================================

def get_visit_wizard_state(
    db: Session,
    visit_id: str,
    clinic_id: str
) -> dict:

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    steps = {

        "step_1_vitals":
            visit.vitals is not None,

        "step_2_consultation":
            (
                visit.homeopathy_case is not None
                or
                visit.allopathy_rx is not None
            ),

        "step_3_billing":
            (
                visit.payment_status
                == PaymentStatus.PAID
            ),

        "step_4_complete":
            visit.closed_at is not None
    }

    if not steps["step_1_vitals"]:

        current_step = 1

    elif not steps["step_2_consultation"]:

        current_step = 2

    elif not steps["step_3_billing"]:

        current_step = 3

    else:

        current_step = 4

    return {

        "visit_id":
            visit_id,

        "visit_type":
            (
                visit.type.value
                if visit.type else None
            ),

        "visit_status":
            visit.visit_status,

        "current_step":
            current_step,

        "steps":
            steps,

        "patient_id":
            visit.patient_id
    }


# =====================================================
# GET VISIT
# =====================================================

def get_visit(
    db: Session,
    visit_id: str,
    clinic_id: str
) -> dict:

    visit = _get_visit(
        db,
        visit_id,
        clinic_id
    )

    result = {

        "id":
            visit.id,

        "patient_id":
            visit.patient_id,

        "type":
            (
                visit.type.value
                if visit.type else None
            ),

        "visit_status":
            visit.visit_status,

        "chief_complaint":
            visit.chief_complaint,

        "disease_type":
            visit.disease_type,

        "fee":
            float(visit.fee or 0),

        "payment_status":
            (
                visit.payment_status.value
                if visit.payment_status
                else None
            ),

        "payment_mode":
            (
                visit.payment_mode.value
                if visit.payment_mode
                else None
            ),

        "visit_date":
            (
                visit.visit_date.strftime(
                    "%d-%m-%Y %H:%M"
                )
                if visit.visit_date else None
            ),

        "closed_at":
            (
                visit.closed_at.strftime(
                    "%d-%m-%Y %H:%M"
                )
                if visit.closed_at else None
            ),

        "notes":
            visit.notes
    }

    return result


# =====================================================
# PRIVATE HELPER
# =====================================================

def _get_visit(
    db: Session,
    visit_id: str,
    clinic_id: str
) -> Visit:

    visit = db.query(Visit).filter(

        Visit.id == visit_id,

        Visit.clinic_id == clinic_id

    ).first()

    if not visit:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found"
        )

    return visit