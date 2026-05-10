from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import billing_service

from app.middleware.auth_middleware import (
    receptionist_or_doctor
)

from app.models.user import User


router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


# =========================================================
# Get Payment Details
# =========================================================
@router.get("/visit/{visit_id}")
def get_payment(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    """
    Get payment details for a visit
    """

    payment = billing_service.get_payment_by_visit(
        db,
        visit_id,
        current_user.clinic_id
    )

    return {
        "id": payment.id,
        "visit_id": payment.visit_id,
        "amount": float(payment.amount),

        "mode": (
            payment.mode.value
            if payment.mode
            else None
        ),

        "transaction_ref": payment.transaction_ref,

        # Supabase public URL
        "receipt_url": payment.receipt_url,

        "created_at": (
            payment.created_at.strftime("%d-%m-%Y %H:%M")
            if payment.created_at
            else None
        )
    }


# =========================================================
# Generate Receipt
# =========================================================
@router.post("/receipt/{visit_id}")
def generate_receipt(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    """
    Generate PDF receipt for closed visit.
    Uploads to Supabase Storage.
    Returns permanent public URL.
    """

    return billing_service.generate_receipt(
        db,
        visit_id,
        current_user.clinic_id
    )


# =========================================================
# Open / Download Receipt
# =========================================================
@router.get("/receipt/{visit_id}/download")
def download_receipt(
    visit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(receptionist_or_doctor)
):
    """
    Redirect user to Supabase public receipt URL.
    Frontend can open/download directly.
    """

    result = billing_service.generate_receipt(
        db,
        visit_id,
        current_user.clinic_id
    )

    pdf_url = result.get("pdf_url")

    if not pdf_url:
        raise HTTPException(
            status_code=404,
            detail="Receipt URL not found"
        )

    return RedirectResponse(
        url=pdf_url
    )