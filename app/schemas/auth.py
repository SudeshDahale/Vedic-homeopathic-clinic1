# =====================================================
# FILE: app/schemas/auth.py
# =====================================================

from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    """
    Create Doctor or Receptionist account
    (used internally after clinic signup)
    """
    name: str
    phone: str
    email: Optional[EmailStr] = None
    password: str
    role: str = "RECEPTIONIST"
    clinic_id: str


class SignupRequest(BaseModel):
    """
    Public clinic signup
    Creates clinic + doctor account together
    """
    clinic_name: str
    doctor_name: str
    qualification: Optional[str] = "B.H.M.S."
    email: EmailStr
    phone: str
    password: str
    city: Optional[str] = None
    timings: Optional[str] = None


class LoginRequest(BaseModel):
    """
    Login with email OR phone
    """
    login: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str
    clinic_id: str
    clinic_name: Optional[str] = ""
    user_id: str


class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str]
    role: str
    clinic_id: str
    is_active: bool

    class Config:
        from_attributes = True