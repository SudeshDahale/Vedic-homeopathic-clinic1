from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate

def get_next_reg_no(db: Session, clinic_id: str) -> int:
    """
    WHY: Each clinic has its own reg number sequence.
    Dr. Jomivale is at reg no. 67 — new patients continue from 68, 69...
    """
    max_reg = db.query(func.max(Patient.reg_no)).filter(
        Patient.clinic_id == clinic_id
    ).scalar()
    return (max_reg or 0) + 1

def create_patient(db: Session, data: PatientCreate, clinic_id: str) -> Patient:
    """
    Register new patient.
    Auto-assigns next reg_no for the clinic.
    """
    patient = Patient(
        clinic_id    = clinic_id,
        reg_no       = get_next_reg_no(db, clinic_id),
        title        = data.title,
        first_name   = data.first_name,
        middle_name  = data.middle_name,
        last_name    = data.last_name,
        dob          = data.dob,
        age          = data.age,
        gender       = data.gender,
        marital_status = data.marital_status,
        res_address  = data.res_address,
        res_city     = data.res_city,
        res_state    = data.res_state,
        res_postal   = data.res_postal,
        res_country  = data.res_country or "India",
        off_address  = data.off_address,
        off_city     = data.off_city,
        off_state    = data.off_state,
        off_postal   = data.off_postal,
        phone_mobile = data.phone_mobile,
        phone_res    = data.phone_res,
        phone_office = data.phone_office,
        fax          = data.fax,
        email        = data.email,
        referred_by_name    = data.referred_by_name,
        referred_by_contact = data.referred_by_contact,
        language_pref = data.language_pref or "en",
        patient_type  = data.patient_type or "HOMEOPATHY",
        anniversary   = data.anniversary
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

def get_patients(db: Session, clinic_id: str,
                 search: str = None, skip: int = 0,
                 limit: int = 50) -> list:
    """
    List patients with optional search.
    WHY search by name + phone: Receptionist types partial name
    or last 4 digits of phone — finds patient instantly.
    """
    query = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.is_active == True
    )

    if search:
        query = query.filter(
            or_(
                Patient.first_name.ilike(f"%{search}%"),
                Patient.last_name.ilike(f"%{search}%"),
                Patient.phone_mobile.ilike(f"%{search}%"),
                Patient.middle_name.ilike(f"%{search}%")
            )
        )

    return query.order_by(
        Patient.created_at.desc()
    ).offset(skip).limit(limit).all()

def get_patient_by_id(db: Session, patient_id: str, clinic_id: str) -> Patient:
    """Get one patient — verify they belong to this clinic"""
    patient = db.query(Patient).filter(
        Patient.id        == patient_id,
        Patient.clinic_id == clinic_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )
    return patient

def update_patient(db: Session, patient_id: str,
                   clinic_id: str, data: PatientUpdate) -> Patient:
    """Update only the fields that were sent"""
    patient = get_patient_by_id(db, patient_id, clinic_id)

    # Only update fields that are actually provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return patient

def get_patient_history(db: Session, patient_id: str, clinic_id: str) -> dict:
    """
    Full patient timeline — all visits, vitals, prescriptions.
    WHY: Doctor needs to see complete history in one view
    before starting new consultation. No flipping through paper files.
    """
    patient = get_patient_by_id(db, patient_id, clinic_id)

    from app.models.visit import Visit
    visits = db.query(Visit).filter(
        Visit.patient_id == patient_id
    ).order_by(Visit.visit_date.desc()).all()

    history = []
    for v in visits:
        entry = {
            "visit_id":       v.id,
            "date":           v.visit_date.strftime("%d-%m-%Y"),
            "type":           v.type.value if v.type else None,
            "chief_complaint": v.chief_complaint,
            "fee":            float(v.fee or 0),
            "payment_status": v.payment_status.value if v.payment_status else None,
        }

        # Add vitals if recorded
        if v.vitals:
            entry["vitals"] = {
                "weight":       float(v.vitals.weight_kg or 0),
                "height":       float(v.vitals.height_cm or 0),
                "bp":           f"{v.vitals.bp_systolic}/{v.vitals.bp_diastolic}",
                "temperature":  float(v.vitals.temperature or 0)
            }

        # Add remedy if homeopathy
        if v.homeopathy_case:
            entry["remedy"]  = v.homeopathy_case.remedy
            entry["potency"] = v.homeopathy_case.potency

        history.append(entry)

    return {
        "patient":      {
            "id":         patient.id,
            "reg_no":     patient.reg_no,
            "name":       f"{patient.first_name} {patient.last_name or ''}".strip(),
            "phone":      patient.phone_mobile,
            "total_visits": patient.total_visits
        },
        "visits":       history,
        "total_visits": len(history)
    }