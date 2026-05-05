import json
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.visit import (
    Visit, VisitType, PaymentStatus, PaymentMode,
    AllopathyRx, HomeopathyCase, Vitals
)
from app.models.billing import Payment
from app.schemas.visit import (
    VisitCreate, VitalsInput, AllopathyInput,
    HomeopathyInput, CloseVisitInput
)
from app.services.growth_service import schedule_followups, update_patient_stats
import pytz

IST = pytz.timezone("Asia/Kolkata")


def create_visit(db: Session, data: VisitCreate,
                 clinic_id: str, doctor_id: str) -> Visit:
    """
    Start a new visit.
    Fee is optional here — receptionist enters it at close time.
    WHY: Doctor may not know exact fee at visit start.
    Fee is confirmed at end after consultation.
    """
    visit = Visit(
        clinic_id       = clinic_id,
        patient_id      = data.patient_id,
        doctor_id       = doctor_id,
        type            = (VisitType.ALLOPATHY
                           if data.type == "ALLOPATHY"
                           else VisitType.HOMEOPATHY),
        chief_complaint = data.chief_complaint,
        disease_type    = data.disease_type or "default",
        fee             = data.fee or 0,
        notes           = data.notes,
        episode_id      = data.episode_id,
        visit_date      = datetime.now(IST)
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def save_vitals(db: Session, visit_id: str,
                clinic_id: str, data: VitalsInput) -> dict:
    """Record BP, weight, height before doctor sees patient"""
    visit = _get_visit(db, visit_id, clinic_id)

    vitals = visit.vitals
    if not vitals:
        vitals = Vitals(visit_id=visit_id)
        db.add(vitals)

    vitals.weight_kg    = data.weight_kg
    vitals.height_cm    = data.height_cm
    vitals.bp_systolic  = data.bp_systolic
    vitals.bp_diastolic = data.bp_diastolic
    vitals.temperature  = data.temperature
    vitals.pulse_rate   = data.pulse_rate

    db.commit()

    return {
        "message":      "Vitals saved",
        "weight_kg":    data.weight_kg,
        "height_cm":    data.height_cm,
        "bp":           f"{data.bp_systolic}/{data.bp_diastolic}",
        "temperature":  data.temperature,
        "pulse_rate":   data.pulse_rate
    }


def save_allopathy_rx(db: Session, visit_id: str,
                      clinic_id: str, data: AllopathyInput) -> dict:
    """
    Save allopathy prescription.
    Medicines stored as JSON list — each item has name, dosage,
    frequency, duration, instructions.
    """
    visit = _get_visit(db, visit_id, clinic_id)

    rx = visit.allopathy_rx
    if not rx:
        rx = AllopathyRx(visit_id=visit_id)
        db.add(rx)

    rx.medicines       = json.dumps([m.model_dump() for m in data.medicines])
    rx.advice          = data.advice
    rx.next_visit_date = data.next_visit_date

    db.commit()

    return {
        "message":         "Prescription saved",
        "medicines_count": len(data.medicines),
        "advice":          data.advice,
        "next_visit_date": str(data.next_visit_date or "")
    }


def save_homeopathy_case(db: Session, visit_id: str,
                         clinic_id: str, data: HomeopathyInput) -> dict:
    """
    Save complete homeopathy case sheet.
    Rubrics and particulars stored as JSON — flexible structure,
    doctor can add any number of rubrics per case.
    """
    visit = _get_visit(db, visit_id, clinic_id)

    case = visit.homeopathy_case
    if not case:
        case = HomeopathyCase(visit_id=visit_id)
        db.add(case)

    case.chief_complaint   = data.chief_complaint
    case.history_present   = data.history_present
    case.history_past      = data.history_past
    case.history_surgical  = data.history_surgical
    case.history_family    = data.history_family
    case.thermal_sensation = data.thermal_sensation
    case.appetite          = data.appetite
    case.thirst            = data.thirst
    case.sleep             = data.sleep
    case.dreams            = data.dreams
    case.menstrual         = data.menstrual
    case.mind_symptoms     = data.mind_symptoms
    case.particulars       = json.dumps(data.particulars or {})
    case.rubrics           = json.dumps(
        [r.model_dump() for r in data.rubrics] if data.rubrics else []
    )
    case.remedy            = data.remedy
    case.potency           = data.potency
    case.repetition        = data.repetition
    case.miasm             = data.miasm

    db.commit()

    return {
        "message":       "Homeopathy case saved",
        "remedy":        data.remedy,
        "potency":       data.potency,
        "rubrics_count": len(data.rubrics) if data.rubrics else 0
    }


def close_visit(db: Session, visit_id: str,
                clinic_id: str, data: CloseVisitInput) -> dict:
    """
    Close visit — triggers full automation chain.

    WHY this matters for revenue:
    1. Fee recorded — goes into daily/monthly revenue totals
    2. Patient stats updated — total_visits, total_spent, value_score
    3. Follow-ups auto-scheduled — patient gets reminder, returns = more revenue
    4. is_missed flag reset — patient no longer in missed list

    Both Allopathy and Homeopathy:
    Fee is ALWAYS manually entered here. No fixed fee ever.
    """
    visit = _get_visit(db, visit_id, clinic_id)

    if visit.closed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit is already closed"
        )

    # Validate payment mode
    try:
        pay_mode = PaymentMode[data.payment_mode.upper()]
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid payment mode: {data.payment_mode}. Use CASH | UPI | ONLINE | CARD"
        )

    # Save fee and mark paid
    visit.fee            = data.fee
    visit.disease_type   = data.disease_type or visit.disease_type or "default"
    visit.payment_status = PaymentStatus.PAID
    visit.payment_mode   = pay_mode
    visit.closed_at      = datetime.now(IST)

    # Create payment record
    payment = Payment(
        visit_id = visit_id,
        amount   = data.fee,
        mode     = pay_mode
    )
    db.add(payment)
    db.commit()

    # Update patient lifetime stats
    update_patient_stats(db, visit.patient_id, float(data.fee))

    # Auto-schedule follow-up reminders based on disease type
    followups = schedule_followups(
        db           = db,
        visit_id     = visit_id,
        patient_id   = visit.patient_id,
        clinic_id    = clinic_id,
        disease_type = visit.disease_type,
        channel      = data.followup_channel or "WHATSAPP"
    )

    return {
        "status":              "closed",
        "visit_id":            visit_id,
        "amount_paid":         float(data.fee),
        "payment_mode":        data.payment_mode.upper(),
        "followups_scheduled": followups,
        "followups_count":     len(followups),
        "message":             f"Visit closed. {len(followups)} follow-up reminders scheduled automatically."
    }


def get_visit(db: Session, visit_id: str, clinic_id: str) -> dict:
    """Get complete visit details — all sub-records included"""
    visit = _get_visit(db, visit_id, clinic_id)

    result = {
        "id":              visit.id,
        "patient_id":      visit.patient_id,
        "type":            visit.type.value if visit.type else None,
        "chief_complaint": visit.chief_complaint,
        "disease_type":    visit.disease_type,
        "fee":             float(visit.fee or 0),
        "payment_status":  visit.payment_status.value if visit.payment_status else None,
        "payment_mode":    visit.payment_mode.value if visit.payment_mode else None,
        "visit_date":      visit.visit_date.strftime("%d-%m-%Y %H:%M") if visit.visit_date else None,
        "closed_at":       visit.closed_at.strftime("%d-%m-%Y %H:%M") if visit.closed_at else None,
        "notes":           visit.notes
    }

    if visit.vitals:
        result["vitals"] = {
            "weight_kg":   float(visit.vitals.weight_kg or 0),
            "height_cm":   float(visit.vitals.height_cm or 0),
            "bp":          f"{visit.vitals.bp_systolic}/{visit.vitals.bp_diastolic}",
            "temperature": float(visit.vitals.temperature or 0),
            "pulse_rate":  visit.vitals.pulse_rate
        }

    if visit.homeopathy_case:
        hc = visit.homeopathy_case
        result["homeopathy_case"] = {
            "chief_complaint":   hc.chief_complaint,
            "history_present":   hc.history_present,
            "history_past":      hc.history_past,
            "thermal_sensation": hc.thermal_sensation,
            "appetite":          hc.appetite,
            "thirst":            hc.thirst,
            "sleep":             hc.sleep,
            "mind_symptoms":     hc.mind_symptoms,
            "remedy":            hc.remedy,
            "potency":           hc.potency,
            "repetition":        hc.repetition,
            "miasm":             hc.miasm,
            "rubrics":           json.loads(hc.rubrics) if hc.rubrics else []
        }

    if visit.allopathy_rx:
        result["prescription"] = {
            "medicines":       json.loads(visit.allopathy_rx.medicines or "[]"),
            "advice":          visit.allopathy_rx.advice,
            "next_visit_date": str(visit.allopathy_rx.next_visit_date or "")
        }

    return result


# ── Private helper ─────────────────────────────────────────
def _get_visit(db: Session, visit_id: str, clinic_id: str) -> Visit:
    visit = db.query(Visit).filter(
        Visit.id        == visit_id,
        Visit.clinic_id == clinic_id
    ).first()
    if not visit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit not found"
        )
    return visit