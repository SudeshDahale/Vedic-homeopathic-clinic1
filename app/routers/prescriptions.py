import json
import tempfile

from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.models.visit import Visit

from app.models.patient import Patient

from app.models.clinic import Clinic

from app.services.pdf_service import (
    generate_prescription_pdf
)

from app.utils.storage import upload_pdf


# =====================================================
# GENERATE PRESCRIPTION
# =====================================================

def generate_prescription(
    db: Session,
    visit_id: str,
    clinic_id: str
) -> dict:
    """
    Generate prescription PDF
    and upload to storage.
    """

    # =================================================
    # GET VISIT
    # =================================================

    visit = db.query(Visit).filter(

        Visit.id == visit_id,

        Visit.clinic_id == clinic_id

    ).first()

    if not visit:

        raise HTTPException(

            status_code=404,

            detail="Visit not found"
        )

    # =================================================
    # GET PATIENT
    # =================================================

    patient = db.query(Patient).filter(

        Patient.id == visit.patient_id

    ).first()

    if not patient:

        raise HTTPException(

            status_code=404,

            detail="Patient not found"
        )

    # =================================================
    # GET CLINIC
    # =================================================

    clinic = db.query(Clinic).filter(

        Clinic.id == clinic_id

    ).first()

    # =================================================
    # DETECT VISIT TYPE
    # =================================================

    visit_type = (

        str(visit.type).upper()

        if visit.type

        else "HOMEOPATHY"
    )

    # =================================================
    # BUILD RX / NOTES
    # =================================================

    rx_notes = ""

    # -------------------------------------------------
    # ALLOPATHY
    # -------------------------------------------------

    if visit.allopathy_rx:

        rx = visit.allopathy_rx

        medicines = []

        if rx.medicines:

            try:

                medicines = json.loads(
                    rx.medicines
                )

            except Exception:

                medicines = []

        for med in medicines:

            rx_notes += (

                f"• {med.get('name', '')} | "

                f"{med.get('dosage', '')} | "

                f"{med.get('frequency', '')} | "

                f"{med.get('duration', '')}\n"
            )

        if rx.advice:

            rx_notes += (

                f"\nAdvice: "

                f"{rx.advice}\n"
            )

    # -------------------------------------------------
    # HOMEOPATHY
    # -------------------------------------------------

    elif visit.homeopathy_case:

        hc = visit.homeopathy_case

        rx_notes += (

            f"Remedy: "

            f"{hc.remedy or ''}\n"
        )

        rx_notes += (

            f"Potency: "

            f"{hc.potency or ''}\n"
        )

        rx_notes += (

            f"Repetition: "

            f"{hc.repetition or ''}\n"
        )

        if hc.miasm:

            rx_notes += (

                f"Miasm: "

                f"{hc.miasm}\n"
            )

    # =================================================
    # BUILD VISIT DICT
    # =================================================

    visit_dict = {

        "id":
            visit.id,

        "rx":
            rx_notes,

        "notes":
            visit.notes,

        "chief_complaint":
            visit.chief_complaint,

        "visit_type":
            visit_type
    }

    # =================================================
    # BUILD CLINIC DICT
    # =================================================

    clinic_dict = {}

    if clinic:

        clinic_dict = {

            "name":
                clinic.name,

            "doctor_name":
                clinic.doctor_name,

            "qualification":
                clinic.qualification,

            "address":
                clinic.address,

            "phone":
                clinic.phone,

            "timings":
                clinic.timings,

            "logo_url":
                getattr(
                    clinic,
                    "logo_url",
                    None
                ),

            "signature_url":
                getattr(
                    clinic,
                    "signature_url",
                    None
                ),

            "reg_number":
                getattr(
                    clinic,
                    "registration_number",
                    ""
                )
        }

    # =================================================
    # BUILD PATIENT DICT
    # =================================================

    patient_dict = {

        "name":
            (
                f"{getattr(patient, 'first_name', '')} "
                f"{getattr(patient, 'last_name', '') or ''}"
            ).strip(),

        "age":
            getattr(
                patient,
                "age",
                ""
            ),

        "gender":
            (
                str(patient.gender)
                if getattr(
                    patient,
                    "gender",
                    None
                )
                else ""
            ),

        "reg_no":
            getattr(
                patient,
                "reg_no",
                ""
            )
    }

    # =================================================
    # BUILD DOCTOR DICT
    # =================================================

    doctor_dict = {

        "name":
            (
                clinic.doctor_name
                if clinic
                else "Doctor"
            ),

        "qualification":
            (
                clinic.qualification
                if clinic
                else "B.H.M.S."
            )
    }

    # =================================================
    # GENERATE PDF BYTES
    # =================================================

    pdf_bytes = generate_prescription_pdf(

        visit=visit_dict,

        clinic=clinic_dict,

        doctor=doctor_dict,

        patient=patient_dict
    )

    # =================================================
    # SAVE TEMP FILE
    # =================================================

    with tempfile.NamedTemporaryFile(

        delete=False,

        suffix=".pdf"

    ) as temp_pdf:

        temp_pdf.write(pdf_bytes)

        pdf_path = temp_pdf.name

    # =================================================
    # UPLOAD TO STORAGE
    # =================================================

    pdf_url = upload_pdf(

        pdf_path,

        folder="prescriptions"
    )

    # =================================================
    # RESPONSE
    # =================================================

    return {

        "message":
            "Prescription generated successfully",

        "pdf_url":
            pdf_url,

        "visit_id":
            visit_id,

        "patient":
            patient_dict["name"],

        "visit_type":
            visit_type
    }