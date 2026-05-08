from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
from app.enums import UserRole

class User(BaseModel):
    __tablename__ = "users"

    clinic_id    = Column(String, nullable=False, index=True)
    role         = Column(String, default=UserRole.RECEPTIONIST)
    name         = Column(String, nullable=False)
    phone        = Column(String, nullable=True, index=True)
    email        = Column(String, nullable=True, index=True)
    password     = Column(String, nullable=False)
    is_active    = Column(Boolean, default=True)

    # Relationships
    visits = relationship("Visit", back_populates="doctor")