from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import enum

class VisitType(str, enum.Enum):
    ALLOPATHY  = "ALLOPATHY"
    HOMEOPATHY = "HOMEOPATHY"

class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PAID    = "PAID"
    WAIVED  = "WAIVED"

class PaymentMode(str, enum.Enum):
    CASH   = "CASH"
    UPI    = "UPI"
    ONLINE = "ONLINE"
    CARD   = "CARD"

class Visit(BaseModel):
    __tablename__ = "visits"

    clinic_id       = Column(String, nullable=False, index=True)
    patient_id      = Column(String, ForeignKey("patients.id"), nullable=False)
    doctor_id       = Column(String, ForeignKey("users.id"), nullable=False)
    episode_id      = Column(String, nullable=True)  # groups related visits

    type            = Column(SQLEnum(VisitType), nullable=False)
    disease_type    = Column(String, nullable=True)  # for follow-up rules
    chief_complaint = Column(String, nullable=True)
    fee             = Column(Numeric(10, 2), default=0)
    payment_status  = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING)
    payment_mode    = Column(SQLEnum(PaymentMode), nullable=True)
    notes           = Column(String, nullable=True)
    visit_date      = Column(DateTime, default=datetime.utcnow)
    closed_at       = Column(DateTime, nullable=True)

    # Relationships
    patient         = relationship("Patient", back_populates="visits")
    doctor          = relationship("User", back_populates="visits")
    allopathy_rx    = relationship("AllopathyRx", back_populates="visit", uselist=False)
    homeopathy_case = relationship("HomeopathyCase", back_populates="visit", uselist=False)
    vitals          = relationship("Vitals", back_populates="visit", uselist=False)
    payment         = relationship("Payment", back_populates="visit", uselist=False)
    follow_ups      = relationship("FollowUp", back_populates="visit")


class AllopathyRx(BaseModel):
    __tablename__ = "allopathy_rx"

    visit_id        = Column(String, ForeignKey("visits.id"), unique=True)
    medicines       = Column(String, nullable=True)  # JSON string
    advice          = Column(String, nullable=True)
    next_visit_date = Column(DateTime, nullable=True)

    visit           = relationship("Visit", back_populates="allopathy_rx")


class HomeopathyCase(BaseModel):
    __tablename__ = "homeopathy_cases"

    visit_id          = Column(String, ForeignKey("visits.id"), unique=True)

    # Case history
    chief_complaint   = Column(String, nullable=True)
    history_present   = Column(String, nullable=True)
    history_past      = Column(String, nullable=True)
    history_surgical  = Column(String, nullable=True)
    history_family    = Column(String, nullable=True)

    # Homeopathy generals
    thermal_sensation = Column(String, nullable=True)  # HOT | COLD | CHILLY
    appetite          = Column(String, nullable=True)
    thirst            = Column(String, nullable=True)
    sleep             = Column(String, nullable=True)
    dreams            = Column(String, nullable=True)
    menstrual         = Column(String, nullable=True)
    mind_symptoms     = Column(String, nullable=True)

    # Particulars + Rubrics stored as JSON strings
    particulars       = Column(String, nullable=True)
    rubrics           = Column(String, nullable=True)

    # Remedy
    remedy            = Column(String, nullable=True)
    potency           = Column(String, nullable=True)  # 30C | 200C | 1M
    repetition        = Column(String, nullable=True)
    miasm             = Column(String, nullable=True)

    visit             = relationship("Visit", back_populates="homeopathy_case")


class Vitals(BaseModel):
    __tablename__ = "vitals"

    visit_id      = Column(String, ForeignKey("visits.id"), unique=True)
    weight_kg     = Column(Numeric(5, 2), nullable=True)
    height_cm     = Column(Numeric(5, 2), nullable=True)
    bp_systolic   = Column(Integer, nullable=True)
    bp_diastolic  = Column(Integer, nullable=True)
    temperature   = Column(Numeric(4, 1), nullable=True)
    pulse_rate    = Column(Integer, nullable=True)

    visit         = relationship("Visit", back_populates="vitals")