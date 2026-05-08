from sqlalchemy import Column, String, Boolean
from app.models.base import BaseModel
from app.enums import UserRole

class Staff(BaseModel):
    __tablename__ = "staff"

    clinic_id    = Column(String, nullable=False, index=True)
    user_id      = Column(String, nullable=False)  # links to users table
    name         = Column(String, nullable=False)
    phone        = Column(String, nullable=True)
    email        = Column(String, nullable=True)
    role         = Column(String, default=UserRole.RECEPTIONIST)
    permissions  = Column(String, nullable=True)   # JSON string
    is_active    = Column(Boolean, default=True)