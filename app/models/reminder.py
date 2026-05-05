from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum

class FollowUpType(str, enum.Enum):
    THREE_DAY    = "THREE_DAY"
    SEVEN_DAY    = "SEVEN_DAY"
    FIFTEEN_DAY  = "FIFTEEN_DAY"
    MONTHLY      = "MONTHLY"
    CUSTOM       = "CUSTOM"

class FollowUpStatus(str, enum.Enum):
    PENDING  = "PENDING"
    SENT     = "SENT"
    DONE     = "DONE"
    SKIPPED  = "SKIPPED"
    FAILED   = "FAILED"

class Channel(str, enum.Enum):
    WHATSAPP = "WHATSAPP"
    SMS      = "SMS"
    VOICE    = "VOICE"
    EMAIL    = "EMAIL"

class FollowUp(BaseModel):
    __tablename__ = "follow_ups"

    visit_id    = Column(String, ForeignKey("visits.id"), nullable=False)
    patient_id  = Column(String, ForeignKey("patients.id"), nullable=False)
    clinic_id   = Column(String, nullable=False)
    due_date    = Column(DateTime, nullable=False)
    type        = Column(SQLEnum(FollowUpType), nullable=False)
    status      = Column(SQLEnum(FollowUpStatus), default=FollowUpStatus.PENDING)
    channel     = Column(SQLEnum(Channel), default=Channel.WHATSAPP)
    template_id = Column(String, nullable=True)
    sent_at     = Column(DateTime, nullable=True)
    response    = Column(String, nullable=True)

    visit       = relationship("Visit", back_populates="follow_ups")
    patient     = relationship("Patient", back_populates="follow_ups")


class NotificationTemplate(BaseModel):
    __tablename__ = "notification_templates"

    clinic_id    = Column(String, nullable=False)
    template_key = Column(String, nullable=False)  # followup_3d | thankyou
    language     = Column(String, nullable=False)  # en | hi | mr
    channel      = Column(SQLEnum(Channel), nullable=False)
    body         = Column(String, nullable=False)  # {patient_name} {doctor_name}


class Consent(BaseModel):
    __tablename__ = "consents"

    patient_id        = Column(String, ForeignKey("patients.id"), nullable=False)
    # Exact OPD consent from Shree Sai case paper
    consent_text      = Column(String, nullable=False)
    patient_sign_url  = Column(String, nullable=True)
    patient_thumb_url = Column(String, nullable=True)
    attender_name     = Column(String, nullable=True)
    attender_sign_url = Column(String, nullable=True)
    attender_thumb_url = Column(String, nullable=True)
    consent_date      = Column(DateTime, nullable=True)

    patient           = relationship("Patient", back_populates="consents")