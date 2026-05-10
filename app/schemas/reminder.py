# schemas/reminder.py — add this now
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FollowUpCreate(BaseModel):
    patient_id: str
    visit_id: str
    due_date: datetime
    type: str       # THREE_DAY / SEVEN_DAY / etc.
    channel: str = "WHATSAPP"

class FollowUpResponse(BaseModel):
    id: str
    patient_id: str
    due_date: datetime
    status: str
    sent_at: Optional[datetime]

    class Config:
        from_attributes = True