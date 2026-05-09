from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from fastapi import HTTPException, status

from app.models.patient import Patient
from app.schemas.patient import (
    PatientCreate,
    PatientUpdate
)


# =====================================================
# HELPERS
# =====================================================

def get_next_reg_no(
    db: Session,
    clinic_id: str
) -> int:
    """
    Each clinic has independent registration numbering.
    """

    max_reg = db.query(
        func.max(Patient.reg_no)
    ).filter(
        Patient.clinic_id == clinic_id
    ).scalar()

    return (max_reg or 0) + 1


# =====================================================
# CREATE PATIENT
# =====================================================

def create_patient(
    db: Session,
    data: PatientCreate,
    clinic_id: str
) -> Patient:
    """
    Register new patient.
    """

    # -------------------------------------------------
    # ENUM SAFETY FIX
    # Frontend may send:
    # Female / Male / Other
    #
    # PostgreSQL enum expects:
    # FEMALE / MALE / OTHER
    # -------------------------------------------------

    gender = (
        data.gender.upper()
        if data.gender else None
    )

    marital_status = (
        data.marital_status.upper()
        if data.marital_status else None
    )

    patient_type = (
        data.patient_type.upper()
        if data.patient_type else "HOMEOPATHY"
    )

    language_pref = (
        data.language_pref.lower()
        if data.language_pref else "en"
    )

    patient = Patient(

        clinic_id=clinic_id,

        reg_no=get_next_reg_no(
            db,
            clinic_id
        ),

        # Basic Info
        title=data.title,

        first_name=data.first_name,
        middle_name=data.middle_name,
        last_name=data.last_name,

        dob=data.dob,
        age=data.age,

        # ENUM FIX
        gender=gender,
        marital_status=marital_status,

        # Residential Address
        res_address=data.res_address,
        res_city=data.res_city,
        res_state=data.res_state,
        res_postal=data.res_postal,
        res_country=data.res_country or "India",

        # Office Address
        off_address=data.off_address,
        off_city=data.off_city,
        off_state=data.off_state,
        off_postal=data.off_postal,

        # Contact
        phone_mobile=data.phone_mobile,
        phone_res=data.phone_res,
        phone_office=data.phone_office,

        fax=data.fax,
        email=data.email,

        # Referral
        referred_by_name=data.referred_by_name,
        referred_by_contact=data.referred_by_contact,

        # Preferences
        language_pref=language_pref,

        # ENUM FIX
        patient_type=patient_type,

        anniversary=data.anniversary
    )

    db.add(patient)

    db.commit()

    db.refresh(patient)

    return patient


# =====================================================
# GET PATIENTS
# =====================================================

def get_patients(
    db: Session,
    clinic_id: str,
    search: str = None,
    skip: int = 0,
    limit: int = 50
) -> list:
    """
    List/search patients.
    """

    # -------------------------------------------------
    # DEBUG LOGS
    # -------------------------------------------------

    total_all = db.query(Patient).count()

    total_clinic = db.query(Patient).filter(
        Patient.clinic_id == clinic_id
    ).count()

    total_active = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.is_active == True
    ).count()

    print(
        f"DEBUG: Total patients in DB: {total_all}"
    )

    print(
        f"DEBUG: Patients for clinic "
        f"{clinic_id}: {total_clinic}"
    )

    print(
        f"DEBUG: Active patients for clinic "
        f"{clinic_id}: {total_active}"
    )

    # -------------------------------------------------
    # MAIN QUERY
    # -------------------------------------------------

    query = db.query(Patient).filter(
        Patient.clinic_id == clinic_id,
        Patient.is_active == True
    )

    # -------------------------------------------------
    # SEARCH
    # -------------------------------------------------

    if search:

        print(
            f"DEBUG: Search term = {search}"
        )

        query = query.filter(
            or_(

                Patient.first_name.ilike(
                    f"%{search}%"
                ),

                Patient.last_name.ilike(
                    f"%{search}%"
                ),

                Patient.middle_name.ilike(
                    f"%{search}%"
                ),

                Patient.phone_mobile.ilike(
                    f"%{search}%"
                )
            )
        )

    # -------------------------------------------------
    # FETCH RESULTS
    # -------------------------------------------------

    patients = query.order_by(
        Patient.created_at.desc()
    ).offset(skip).limit(limit).all()

    print(
        f"DEBUG: Returning "
        f"{len(patients)} patients"
    )

    return patients


# =====================================================
# GET SINGLE PATIENT
# =====================================================

def get_patient_by_id(
    db: Session,
    patient_id: str,
    clinic_id: str
) -> Patient:

    patient = db.query(Patient).filter(
        Patient.id == patient_id,
        Patient.clinic_id == clinic_id
    ).first()

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return patient


# =====================================================
# UPDATE PATIENT
# =====================================================

def update_patient(
    db: Session,
    patient_id: str,
    clinic_id: str,
    data: PatientUpdate
) -> Patient:

    patient = get_patient_by_id(
        db,
        patient_id,
        clinic_id
    )

    update_data = data.model_dump(
        exclude_unset=True
    )

    # -------------------------------------------------
    # ENUM FIXES
    # -------------------------------------------------

    if "gender" in update_data and update_data["gender"]:
        update_data["gender"] = (
            update_data["gender"].upper()
        )

    if (
        "marital_status" in update_data
        and update_data["marital_status"]
    ):
        update_data["marital_status"] = (
            update_data["marital_status"].upper()
        )

    if (
        "patient_type" in update_data
        and update_data["patient_type"]
    ):
        update_data["patient_type"] = (
            update_data["patient_type"].upper()
        )

    for field, value in update_data.items():
        setattr(patient, field, value)

    db.commit()

    db.refresh(patient)

    return patient


# =====================================================
# PATIENT HISTORY
# =====================================================

def get_patient_history(
    db: Session,
    patient_id: str,
    clinic_id: str
) -> dict:
    """
    Complete patient timeline.
    """

    patient = get_patient_by_id(
        db,
        patient_id,
        clinic_id
    )

    from app.models.visit import Visit

    visits = db.query(Visit).filter(
        Visit.patient_id == patient_id
    ).order_by(
        Visit.visit_date.desc()
    ).all()

    history = []

    for v in visits:

        entry = {

            "visit_id": v.id,

            "date": (
                v.visit_date.strftime("%d-%m-%Y")
                if v.visit_date else ""
            ),

            "type": (
                v.type.value
                if v.type else None
            ),

            "chief_complaint":
                v.chief_complaint,

            "fee":
                float(v.fee or 0),

            "payment_status":
                (
                    v.payment_status.value
                    if v.payment_status
                    else None
                )
        }

        # Vitals
        if v.vitals:

            entry["vitals"] = {

                "weight":
                    float(
                        v.vitals.weight_kg or 0
                    ),

                "height":
                    float(
                        v.vitals.height_cm or 0
                    ),

                "bp":
                    f"{v.vitals.bp_systolic}/"
                    f"{v.vitals.bp_diastolic}",

                "temperature":
                    float(
                        v.vitals.temperature or 0
                    )
            }

        # Homeopathy
        if v.homeopathy_case:

            entry["remedy"] = (
                v.homeopathy_case.remedy
            )

            entry["potency"] = (
                v.homeopathy_case.potency
            )

        history.append(entry)

    return {

        "patient": {

            "id":
                patient.id,

            "reg_no":
                patient.reg_no,

            "name":
                f"{patient.first_name} "
                f"{patient.last_name or ''}".strip(),

            "phone":
                patient.phone_mobile,

            "total_visits":
                patient.total_visits
        },

        "visits":
            history,

        "total_visits":
            len(history)
    }