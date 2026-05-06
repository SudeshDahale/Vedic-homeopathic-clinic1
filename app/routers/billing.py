from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import billing_service
from app.middleware.auth_middleware import (
    get_current_user, receptionist_or_doctor
)
from app.models.user import User
import os

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/visit/{visit_id}")
def get_payment(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """Get payment details for a visit"""
    payment = billing_service.get_payment_by_visit(
        db, visit_id, current_user.clinic_id
    )
    return {
        "id":              payment.id,
        "visit_id":        payment.visit_id,
        "amount":          float(payment.amount),
        "mode":            payment.mode.value if payment.mode else None,
        "transaction_ref": payment.transaction_ref,
        "receipt_url":     payment.receipt_url,
        "created_at":      payment.created_at.strftime("%d-%m-%Y %H:%M") if payment.created_at else None
    }


@router.post("/receipt/{visit_id}")
def generate_receipt(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Generate PDF receipt for a closed visit.
    Call this after closing visit — returns receipt details.
    """
    return billing_service.generate_receipt(
        db, visit_id, current_user.clinic_id
    )


@router.get("/receipt/{visit_id}/download")
def download_receipt(
    visit_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """
    Download receipt PDF.
    Lovable frontend calls this → opens PDF in browser
    or sends via WhatsApp.
    """
    result = billing_service.generate_receipt(
        db, visit_id, current_user.clinic_id
    )
    pdf_path = result["pdf_path"]

    if not os.path.exists(pdf_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Receipt file not found")

    return FileResponse(
        path         = pdf_path,
        media_type   = "application/pdf",
        filename     = f"receipt_{visit_id[:8]}.pdf"
    )