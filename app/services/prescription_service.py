import json
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.visit import Visit, AllopathyRx, HomeopathyCase
from app.models.patient import Patient
from app.models.clinic import Clinic
from app.services.pdf_service import generate_prescription_pdf


def generate_prescription(db: Session, visit_id: str,
                          clinic_id: str) -> dict:
    """
    Generate prescription PDF for any visit type.
    WHY: Printed/WhatsApp prescription builds patient trust.
    Each shared prescription markets Vennova automatically.
    """
    visit = db.query(Visit).filter(
        Visit.id        == visit_id,
        Visit.clinic_id == clinic_id
    ).first()

    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    patient = db.query(Patient).filter(
        Patient.id == visit.patient_id
    ).first()

    clinic = db.query(Clinic).filter(
        Clinic.id == clinic_id
    ).first()

    # Build medicines list
    medicines = []

    # Allopathy prescription
    if visit.allopathy_rx and visit.allopathy_rx.medicines:
        try:
            medicines = json.loads(visit.allopathy_rx.medicines)
        except Exception:
            medicines = []

    # Homeopathy — remedy as medicine
    if visit.homeopathy_case and visit.homeopathy_case.remedy:
        hc = visit.homeopathy_case
        medicines = [{
            "name":         hc.remedy,
            "dosage":       hc.potency or "-",
            "frequency":    hc.repetition or "-",
            "duration":     "As advised",
            "instructions": f"Miasm: {hc.miasm}" if hc.miasm else ""
        }]

    prescription_data = {
        "clinic": {
            "name":          clinic.name if clinic else "Homoeopathic Clinic",
            "doctor_name":   clinic.doctor_name if clinic else "Doctor",
            "qualification": clinic.qualification if clinic else "B.H.M.S.",
            "address":       clinic.address if clinic else "",
            "phone":         clinic.phone if clinic else "",
            "timings":       clinic.timings if clinic else ""
        },
        "patient": {
            "name":         f"{patient.first_name} {patient.last_name or ''}".strip() if patient else "Patient",
            "age":          patient.age if patient else "-",
            "gender":       patient.gender.value if patient and patient.gender else "-",
            "reg_no":       patient.reg_no if patient else 0,
            "total_visits": patient.total_visits if patient else 1
        },
        "visit": {
            "date":            visit.visit_date.strftime("%d-%m-%Y") if visit.visit_date else "",
            "chief_complaint": visit.chief_complaint or "-",
            "type":            visit.type.value if visit.type else ""
        },
        "prescription": {
            "medicines":       medicines,
            "advice":          visit.allopathy_rx.advice if visit.allopathy_rx else None,
            "next_visit_date": str(visit.allopathy_rx.next_visit_date) if visit.allopathy_rx and visit.allopathy_rx.next_visit_date else None
        }
    }

    pdf_path = generate_prescription_pdf(prescription_data)

    return {
        "pdf_path":   pdf_path,
        "visit_id":   visit_id,
        "patient":    prescription_data["patient"]["name"],
        "visit_type": visit.type.value if visit.type else "",
        "message":    "Prescription generated successfully"
    }