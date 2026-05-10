import json
import tempfile
import asyncio

from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.models.visit import Visit

from app.models.patient import Patient

from app.models.clinic import Clinic

from app.services.pdf_service import (
    generate_prescription_pdf
)

from app.services.whatsapp_service import (
    send_text_message
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

        Patient.id == visit.patient_id,

        Patient.clinic_id == clinic_id

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

    if not clinic:

        raise HTTPException(

            status_code=404,

            detail="Clinic not found"
        )

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
                f"\nAdvice: {rx.advice}\n"
            )

    # -------------------------------------------------
    # HOMEOPATHY
    # -------------------------------------------------

    elif visit.homeopathy_case:

        hc = visit.homeopathy_case

        rx_notes += (
            f"Remedy: {hc.remedy or ''}\n"
        )

        rx_notes += (
            f"Potency: {hc.potency or ''}\n"
        )

        rx_notes += (
            f"Repetition: "
            f"{hc.repetition or ''}\n"
        )

        if hc.miasm:

            rx_notes += (
                f"Miasm: {hc.miasm}\n"
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
                f"{patient.first_name} "
                f"{patient.last_name or ''}"
            ).strip(),

        "age":
            patient.age,

        "gender":
            (
                str(patient.gender)
                if patient.gender
                else ""
            ),

        "reg_no":
            (
                patient.reg_no
                if hasattr(patient, "reg_no")
                else ""
            )
    }

    # =================================================
    # BUILD DOCTOR DICT
    # =================================================

    doctor_dict = {

        "name":
            clinic.doctor_name,

        "qualification":
            clinic.qualification or "B.H.M.S."
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
    # SAVE TEMP PDF
    # =================================================

    with tempfile.NamedTemporaryFile(

        delete=False,

        suffix=".pdf"

    ) as temp_pdf:

        temp_pdf.write(pdf_bytes)

        pdf_path = temp_pdf.name

    # =================================================
    # UPLOAD PDF
    # =================================================

    pdf_url = upload_pdf(

        pdf_path,

        folder="prescriptions"
    )

    # =================================================
    # SEND WHATSAPP MESSAGE
    # =================================================

    try:

        if patient.phone_mobile:

            whatsapp_message = (

                f"Hi {patient_dict['name']}, "

                f"your prescription from "

                f"{clinic_dict['doctor_name']} "

                f"is ready:\n\n"

                f"{pdf_url}\n\n"

                f"For queries, call "

                f"{clinic_dict['phone']}"
            )

            # -----------------------------------------
            # HANDLE ASYNC SAFELY
            # -----------------------------------------

            try:

                loop = asyncio.get_running_loop()

                loop.create_task(

                    send_text_message(

                        patient.phone_mobile,

                        whatsapp_message
                    )
                )

            except RuntimeError:

                asyncio.run(

                    send_text_message(

                        patient.phone_mobile,

                        whatsapp_message
                    )
                )

    except Exception as whatsapp_error:

        print(
            f"❌ WhatsApp send failed: "
            f"{whatsapp_error}"
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