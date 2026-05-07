from pydantic import BaseModel
from typing import Optional
from datetime import date

class QueueAdd(BaseModel):
    """Receptionist adds patient to today's queue"""
    patient_id:  str
    visit_type:  Optional[str] = "WALKIN"   # WALKIN | APPOINTMENT
    priority:    Optional[int] = 0           # 0=normal, 1=urgent
    notes:       Optional[str] = None

class QueueResponse(BaseModel):
    id:            str
    token_number:  int
    patient_id:    str
    patient_name:  Optional[str]
    patient_phone: Optional[str]
    status:        str
    visit_type:    str
    priority:      int
    check_in_time: Optional[str]
    called_time:   Optional[str]
    wait_minutes:  Optional[int]
    notes:         Optional[str]

class QueueStats(BaseModel):
    total_today:    int
    waiting:        int
    in_progress:    int
    completed:      int
    no_show:        int
    avg_wait_mins:  float