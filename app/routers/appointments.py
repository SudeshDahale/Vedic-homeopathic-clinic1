from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from app.database import get_db
from app.middleware.auth_middleware import receptionist_or_doctor, get_current_user
from app.models.appointment import Appointment
from app.models.patient import Patient
from app.models.user import User
from app.enums import AppointmentStatus, VisitType
import pytz

IST = pytz.timezone("Asia/Kolkata")
router = APIRouter(prefix="/appointments", tags=["Appointments"])

class AppointmentCreate(BaseModel):
    patient_id:      str
    scheduled_at:    datetime
    visit_type:      Optional[str] = "HOMEOPATHY"
    chief_complaint: Optional[str] = None
    notes:           Optional[str] = None
    duration_mins:   Optional[int] = 30

class AppointmentUpdate(BaseModel):
    scheduled_at:    Optional[datetime] = None
    status:          Optional[str]      = None
    notes:           Optional[str]      = None
    chief_complaint: Optional[str]      = None

def _format_appointment(a: Appointment, patient: Patient) -> dict:
    return {
        "id":              a.id,
        "patient_id":      a.patient_id,
        "patient_name":    f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Unknown",
        "patient_phone":   patient.phone_mobile if patient else None,
        "scheduled_at":    a.scheduled_at.strftime("%d-%m-%Y %H:%M") if a.scheduled_at else None,
        "visit_type":      a.visit_type,
        "status":          a.status,
        "chief_complaint": a.chief_complaint,
        "notes":           a.notes,
        "duration_mins":   a.duration_mins
    }

@router.post("/")
def create_appointment(
    data:         AppointmentCreate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """Book new appointment"""
    patient = db.query(Patient).filter(
        Patient.id        == data.patient_id,
        Patient.clinic_id == current_user.clinic_id
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appt = Appointment(
        clinic_id       = current_user.clinic_id,
        patient_id      = data.patient_id,
        doctor_id       = current_user.id,
        scheduled_at    = data.scheduled_at,
        visit_type      = data.visit_type,
        chief_complaint = data.chief_complaint,
        notes           = data.notes,
        duration_mins   = data.duration_mins
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    return {
        "message":        "Appointment booked",
        "appointment_id": appt.id,
        "patient":        f"{patient.first_name} {patient.last_name or ''}".strip(),
        "scheduled_at":   appt.scheduled_at.strftime("%d-%m-%Y %H:%M")
    }

@router.get("/today")
def get_todays_appointments(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """All appointments for today"""
    now   = datetime.now(IST)
    start = now.replace(hour=0, minute=0, second=0)
    end   = now.replace(hour=23, minute=59, second=59)

    appts = db.query(Appointment).filter(
        and_(
            Appointment.clinic_id    == current_user.clinic_id,
            Appointment.scheduled_at >= start,
            Appointment.scheduled_at <= end
        )
    ).order_by(Appointment.scheduled_at).all()

    result = []
    for a in appts:
        patient = db.query(Patient).filter(Patient.id == a.patient_id).first()
        result.append(_format_appointment(a, patient))

    return {"date": str(now.date()), "total": len(result), "appointments": result}

@router.put("/{appointment_id}")
def update_appointment(
    appointment_id: str,
    data:           AppointmentUpdate,
    db:             Session = Depends(get_db),
    current_user:   User    = Depends(receptionist_or_doctor)
):
    """Update or cancel appointment"""
    appt = db.query(Appointment).filter(
        Appointment.id        == appointment_id,
        Appointment.clinic_id == current_user.clinic_id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(appt, key, value)

    db.commit()
    return {"message": "Appointment updated", "id": appointment_id}