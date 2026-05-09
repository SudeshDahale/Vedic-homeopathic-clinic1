from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import razorpay, os
from datetime import datetime, timedelta
import pytz

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.models.clinic import Clinic

router = APIRouter(prefix="/subscription", tags=["Subscription"])

IST = pytz.timezone("Asia/Kolkata")

PLAN_MAP = {
    "starter_monthly":    "RAZORPAY_STARTER_MONTHLY",
    "starter_yearly":     "RAZORPAY_STARTER_YEARLY",
    "growth_monthly":     "RAZORPAY_GROWTH_MONTHLY",
    "growth_yearly":      "RAZORPAY_GROWTH_YEARLY",
    "clinicpro_monthly":  "RAZORPAY_CLINICPRO_MONTHLY",
    "clinicpro_yearly":   "RAZORPAY_CLINICPRO_YEARLY",
}

PLAN_LIMITS = {
    "starter":   {"max_patients_per_month": 100, "max_staff": 0, "max_doctors": 1},
    "growth":    {"max_patients_per_month": -1,  "max_staff": 3, "max_doctors": 1},
    "clinicpro": {"max_patients_per_month": -1,  "max_staff": -1,"max_doctors": 5},
}

def get_razorpay_client():
    return razorpay.Client(
        auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
    )


class CreateSubscriptionRequest(BaseModel):
    plan_key: str  # e.g. "growth_monthly"


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id:    str
    razorpay_subscription_id: str
    razorpay_signature:     str


@router.get("/status")
def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if not clinic:
        raise HTTPException(404, "Clinic not found")

    days_left = None
    if clinic.trial_end_date:
        delta = clinic.trial_end_date.replace(tzinfo=IST) - datetime.now(IST)
        days_left = max(0, delta.days)

    return {
        "subscription_status": clinic.subscription_status,
        "plan":                clinic.subscription_plan or "trial",
        "trial_end_date":      clinic.trial_end_date,
        "days_left":           days_left,
        "razorpay_sub_id":     clinic.razorpay_subscription_id,
    }


@router.post("/create")
def create_subscription(
    data: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if data.plan_key not in PLAN_MAP:
        raise HTTPException(400, f"Invalid plan. Choose from: {list(PLAN_MAP.keys())}")

    plan_id = os.getenv(PLAN_MAP[data.plan_key])
    if not plan_id:
        raise HTTPException(500, "Plan not configured in env vars")

    client = get_razorpay_client()

    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()

    subscription = client.subscription.create({
        "plan_id":        plan_id,
        "total_count":    120,      # 10 years max
        "quantity":       1,
        "customer_notify": 1,
        "notes": {
            "clinic_id":   str(current_user.clinic_id),
            "clinic_name": clinic.name if clinic else "",
            "plan_key":    data.plan_key,
        }
    })

    return {
        "subscription_id": subscription["id"],
        "plan_key":        data.plan_key,
        "razorpay_key":    os.getenv("RAZORPAY_KEY_ID"),
        "clinic_name":     clinic.name if clinic else "",
        "clinic_email":    current_user.email,
    }


@router.post("/verify")
def verify_payment(
    data: VerifyPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    client = get_razorpay_client()

    # Verify signature
    try:
        client.utility.verify_payment_signature({
            "razorpay_payment_id":       data.razorpay_payment_id,
            "razorpay_subscription_id":  data.razorpay_subscription_id,
            "razorpay_signature":        data.razorpay_signature,
        })
    except Exception:
        raise HTTPException(400, "Payment signature invalid — possible fraud")

    # Get subscription details
    sub = client.subscription.fetch(data.razorpay_subscription_id)
    plan_key = sub.get("notes", {}).get("plan_key", "growth_monthly")
    tier     = plan_key.split("_")[0]  # "starter" / "growth" / "clinicpro"
    period   = plan_key.split("_")[1]  # "monthly" / "yearly"

    # Update clinic
    clinic = db.query(Clinic).filter(Clinic.id == current_user.clinic_id).first()
    if clinic:
        clinic.subscription_status      = "ACTIVE"
        clinic.subscription_plan        = tier
        clinic.subscription_period      = period
        clinic.razorpay_subscription_id = data.razorpay_subscription_id
        clinic.subscription_start_date  = datetime.now(IST)

        limits = PLAN_LIMITS.get(tier, PLAN_LIMITS["growth"])
        clinic.max_patients_per_month   = limits["max_patients_per_month"]
        clinic.max_staff                = limits["max_staff"]
        clinic.max_doctors              = limits["max_doctors"]

        db.commit()

    return {
        "status":  "activated",
        "plan":    tier,
        "period":  period,
        "message": f"Welcome to Vennova {tier.title()}!"
    }


@router.post("/webhook")
async def razorpay_webhook(
    request,
    db: Session = Depends(get_db)
):
    """
    Razorpay sends events here for subscription renewals,
    failures, and cancellations. No auth — uses signature.
    """
    import hmac, hashlib, json
    body      = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    secret    = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    expected = hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(400, "Invalid webhook signature")

    event = json.loads(body)
    etype = event.get("event")

    if etype == "subscription.charged":
        sub_id = event["payload"]["subscription"]["entity"]["id"]
        clinic = db.query(Clinic).filter(
            Clinic.razorpay_subscription_id == sub_id
        ).first()
        if clinic:
            clinic.subscription_status = "ACTIVE"
            db.commit()

    elif etype in ("subscription.cancelled", "subscription.expired"):
        sub_id = event["payload"]["subscription"]["entity"]["id"]
        clinic = db.query(Clinic).filter(
            Clinic.razorpay_subscription_id == sub_id
        ).first()
        if clinic:
            clinic.subscription_status = "EXPIRED"
            db.commit()

    return {"status": "ok"}