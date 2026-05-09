from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Integer
)

from sqlalchemy.orm import relationship

from app.models.base import BaseModel

from app.enums import (
    SubscriptionPlan,
    SubscriptionStatus
)


class Clinic(BaseModel):

    __tablename__ = "clinics"

    # =================================================
    # BASIC INFO
    # =================================================

    name = Column(
        String,
        nullable=False
    )

    doctor_name = Column(
        String,
        nullable=False
    )

    qualification = Column(
        String,
        nullable=True
    )

    address = Column(
        String,
        nullable=True
    )

    city = Column(
        String,
        nullable=True
    )

    phone = Column(
        String,
        nullable=True
    )

    email = Column(
        String,
        nullable=True
    )

    logo_url = Column(
        String,
        nullable=True
    )

    signature_url = Column(
        String,
        nullable=True
    )

    timings = Column(
        String,
        nullable=True
    )

    # =================================================
    # CLINIC TYPE
    # =================================================
    # HOMEOPATHY
    # ALLOPATHY
    # AYURVEDIC
    # MULTI
    # =================================================

    clinic_type = Column(
        String,
        default="HOMEOPATHY"
    )

    # =================================================
    # SUBSCRIPTION
    # =================================================

    plan_id = Column(
        String,
        default=SubscriptionPlan.STARTER
    )

    subscription_status = Column(
        String,
        default=SubscriptionStatus.TRIAL
    )

    trial_end_date = Column(
        DateTime,
        nullable=True
    )

    staff_limit = Column(
        Integer,
        default=2
    )

    # =================================================
    # BRANDING
    # =================================================
    # GROWTH + ENTERPRISE ONLY
    # =================================================

    branding_enabled = Column(
        Boolean,
        default=False
    )

    custom_logo = Column(
        String,
        nullable=True
    )

    primary_color = Column(
        String,
        default="#16a34a"
    )

    secondary_color = Column(
        String,
        default="#2563eb"
    )

    # =================================================
    # ONBOARDING STATUS SYSTEM
    # =================================================
    # Tracks setup completion progress
    # =================================================

    onboarding_complete = Column(
        Boolean,
        default=False
    )

    has_logo = Column(
        Boolean,
        default=False
    )

    has_signature = Column(
        Boolean,
        default=False
    )

    has_whatsapp = Column(
        Boolean,
        default=False
    )

    has_first_patient = Column(
        Boolean,
        default=False
    )

    has_first_consultation = Column(
        Boolean,
        default=False
    )

    onboarding_dismissed = Column(
        Boolean,
        default=False
    )

    # =================================================
    # SETTINGS
    # =================================================

    is_active = Column(
        Boolean,
        default=True
    )