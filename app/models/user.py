from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class UserRole(str, enum.Enum):
    DOCTOR = "DOCTOR"
    RECEPTIONIST = "RECEPTIONIST"


class User(BaseModel):
    __tablename__ = "users"

    clinic_id = Column(String, nullable=False, index=True)

    name = Column(String, nullable=False)

    phone = Column(String, unique=True, nullable=False, index=True)

    email = Column(String, unique=True, nullable=True)

    # ✅ FIXED FIELD NAME
    hashed_password = Column(String, nullable=False)

    role = Column(
        SQLEnum(UserRole),
        default=UserRole.RECEPTIONIST,
        nullable=False
    )

    is_active = Column(Boolean, default=True)

    # Relationships
    visits = relationship("Visit", back_populates="doctor")