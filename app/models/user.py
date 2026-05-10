from sqlalchemy import (
    Column,
    String,
    Boolean,
    Enum as SQLEnum
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel
from app.enums import UserRole


# =========================================================
# User Model
# =========================================================
class User(BaseModel):
    __tablename__ = "users"

    # Clinic Ownership
    clinic_id = Column(
        String,
        nullable=False,
        index=True
    )

    # User Role
    role = Column(
        SQLEnum(UserRole),
        default=UserRole.RECEPTIONIST,
        nullable=False
    )

    # Basic Info
    name = Column(
        String,
        nullable=False
    )

    phone = Column(
        String,
        unique=True,
        nullable=True,
        index=True
    )

    email = Column(
        String,
        unique=True,
        nullable=True,
        index=True
    )

    # SECURE PASSWORD FIELD
    hashed_password = Column(
        String,
        nullable=False
    )

    # Account Status
    is_active = Column(
        Boolean,
        default=True
    )

    # =====================================================
    # Relationships
    # =====================================================
    visits = relationship(
        "Visit",
        back_populates="doctor"
    )