from sqlalchemy import Column, String, Integer, Boolean
from app.models.base import BaseModel
from app.enums import ImportStatus

class ImportJob(BaseModel):
    __tablename__ = "import_jobs"

    clinic_id        = Column(String, nullable=False, index=True)
    uploaded_by      = Column(String, nullable=False)  # user_id
    file_name        = Column(String, nullable=False)
    file_type        = Column(String, nullable=False)   # csv | excel | pdf
    file_url         = Column(String, nullable=True)    # Supabase storage URL
    status           = Column(String, default=ImportStatus.PENDING)
    total_rows       = Column(Integer, default=0)
    processed_rows   = Column(Integer, default=0)
    successful_rows  = Column(Integer, default=0)
    failed_rows      = Column(Integer, default=0)
    error_log        = Column(String, nullable=True)    # JSON string
    completed_at     = Column(String, nullable=True)