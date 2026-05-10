from pydantic import BaseModel
from typing import Optional, List
from datetime import date


# ── Vitals ────────────────────────────────────────────

class VitalsInput(BaseModel):
    weight_kg:    Optional[float] = None
    height_cm:    Optional[float] = None
    bp_systolic:  Optional[int]   = None
    bp_diastolic: Optional[int]   = None
    temperature:  Optional[float] = None
    pulse_rate:   Optional[int]   = None


class VitalsResponse(BaseModel):
    weight_kg:    Optional[float]
    height_cm:    Optional[float]
    bp_systolic:  Optional[int]
    bp_diastolic: Optional[int]
    temperature:  Optional[float]
    pulse_rate:   Optional[int]

    class Config:
        from_attributes = True


# ── Allopathy ─────────────────────────────────────────

class MedicineItem(BaseModel):
    name:         str
    dosage:       str                   # "1 tablet"
    frequency:    str                   # "3 times a day"
    duration:     str                   # "5 days"
    instructions: Optional[str] = None  # "after food"


class AllopathyInput(BaseModel):
    medicines:       List[MedicineItem]
    advice:          Optional[str]  = None
    next_visit_date: Optional[date] = None


class AllopathyResponse(BaseModel):
    medicines:       Optional[list]
    advice:          Optional[str]
    next_visit_date: Optional[str]

    class Config:
        from_attributes = True


# ── Homeopathy ────────────────────────────────────────

class RubricItem(BaseModel):
    text:    str
    grade:   int = 1
    chapter: Optional[str] = None


class HomeopathyInput(BaseModel):

    # History
    chief_complaint:  Optional[str] = None
    history_present:  Optional[str] = None
    history_past:     Optional[str] = None
    history_surgical: Optional[str] = None
    history_family:   Optional[str] = None

    # Generals
    thermal_sensation: Optional[str] = None
    appetite:          Optional[str] = None
    thirst:            Optional[str] = None
    sleep:             Optional[str] = None
    dreams:            Optional[str] = None
    menstrual:         Optional[str] = None
    mind_symptoms:     Optional[str] = None

    # Particulars + Rubrics
    particulars: Optional[dict] = None
    rubrics:     Optional[List[RubricItem]] = None

    # Remedy
    remedy:     Optional[str] = None
    potency:    Optional[str] = None
    repetition: Optional[str] = None
    miasm:      Optional[str] = None


# ── Visit ─────────────────────────────────────────────

class VisitCreate(BaseModel):

    patient_id:      str

    # ALLOPATHY | HOMEOPATHY
    type:            str

    chief_complaint: Optional[str]  = None

    disease_type:    Optional[str]  = "default"

    # -------------------------------------------------
    # IMPORTANT:
    # Fee should NEVER be auto-filled or hardcoded.
    # Receptionist/doctor enters fee manually later
    # while closing the visit.
    # -------------------------------------------------
    fee:             Optional[float] = None

    notes:           Optional[str]  = None

    # Link to existing episode if available
    episode_id:      Optional[str]  = None


# ── Close Visit ───────────────────────────────────────

class CloseVisitInput(BaseModel):
    """
    Receptionist fills this when closing visit.

    Fee is REQUIRED for both:
    - Allopathy
    - Homeopathy

    No fixed/default consultation fee.
    """

    fee:              float

    # CASH | UPI | ONLINE | CARD
    payment_mode:     str

    disease_type:     Optional[str] = "default"

    followup_channel: Optional[str] = "WHATSAPP"


# ── Visit Response ────────────────────────────────────

class VisitResponse(BaseModel):

    id:              str
    patient_id:      str
    type:            str

    chief_complaint: Optional[str]

    disease_type:    Optional[str]

    fee:             Optional[float]

    payment_status:  Optional[str]

    payment_mode:    Optional[str]

    visit_date:      Optional[str]

    closed_at:       Optional[str]

    notes:           Optional[str]

    class Config:
        from_attributes = True