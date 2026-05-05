from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    """Data needed to create a new Doctor or Receptionist account"""
    name:       str
    phone:      str
    email:      Optional[str] = None
    password:   str
    role:       str = "RECEPTIONIST"   # DOCTOR or RECEPTIONIST
    clinic_id:  str

class LoginRequest(BaseModel):
    """Login with phone + password"""
    phone:    str
    password: str

class LoginResponse(BaseModel):
    """What we send back after successful login"""
    access_token: str
    token_type:   str = "bearer"
    role:         str
    name:         str
    clinic_id:    str
    user_id:      str

class UserResponse(BaseModel):
    """Current logged-in user info"""
    id:        str
    name:      str
    phone:     str
    email:     Optional[str]
    role:      str
    clinic_id: str
    is_active: bool

    class Config:
        from_attributes = True