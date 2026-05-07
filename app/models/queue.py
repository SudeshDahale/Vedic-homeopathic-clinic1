from sqlalchemy import Column, String, Integer, DateTime, Date, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from datetime import datetime
import enum
import pytz

IST = pytz.timezone("Asia/Kolkata")

class QueueStatus(str, enum.Enum):
    WAITING     = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    NO_SHOW     = "NO_SHOW"
    SKIPPED     = "SKIPPED"

class VisitTypeQueue(str, enum.Enum):
    WALKIN      = "WALKIN"
    APPOINTMENT = "APPOINTMENT"

class Queue(BaseModel):
    __tablename__ = "queue"

    clinic_id      = Column(String, nullable=False, index=True)
    patient_id     = Column(String, nullable=False, index=True)
    token_number   = Column(Integer, nullable=False)
    queue_date     = Column(Date, nullable=False, index=True)
    visit_type     = Column(SQLEnum(VisitTypeQueue), default=VisitTypeQueue.WALKIN)
    status         = Column(SQLEnum(QueueStatus), default=QueueStatus.WAITING, index=True)
    priority       = Column(Integer, default=0)   # 1 = urgent, 0 = normal
    check_in_time  = Column(DateTime, default=datetime.utcnow)
    called_time    = Column(DateTime, nullable=True)
    start_time     = Column(DateTime, nullable=True)
    end_time       = Column(DateTime, nullable=True)
    notes          = Column(String, nullable=True)
    visit_id       = Column(String, nullable=True)  # linked after visit created