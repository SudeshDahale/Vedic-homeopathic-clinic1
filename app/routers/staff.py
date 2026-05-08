from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.middleware.auth_middleware import doctor_only, get_current_user
from app.models.user import User
from app.enums import UserRole

router = APIRouter(prefix="/staff", tags=["Staff"])

class StaffUpdate(BaseModel):
    name:      Optional[str] = None
    phone:     Optional[str] = None
    email:     Optional[str] = None
    role:      Optional[str] = None
    is_active: Optional[bool] = None

@router.get("/")
def list_staff(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """List all staff for this clinic"""
    staff = db.query(User).filter(
        User.clinic_id == current_user.clinic_id,
        User.role      != UserRole.DOCTOR
    ).all()

    return {
        "total": len(staff),
        "staff": [
            {
                "id":        s.id,
                "name":      s.name,
                "phone":     s.phone,
                "email":     s.email,
                "role":      s.role,
                "is_active": s.is_active
            }
            for s in staff
        ]
    }

@router.put("/{staff_id}")
def update_staff(
    staff_id:     str,
    data:         StaffUpdate,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """Update staff member — doctor only"""
    staff = db.query(User).filter(
        User.id        == staff_id,
        User.clinic_id == current_user.clinic_id
    ).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(staff, key, value)

    db.commit()
    return {"message": "Staff updated", "id": staff_id}

@router.delete("/{staff_id}")
def delete_staff(
    staff_id:     str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(doctor_only)
):
    """Deactivate staff member"""
    staff = db.query(User).filter(
        User.id        == staff_id,
        User.clinic_id == current_user.clinic_id,
        User.role      != UserRole.DOCTOR
    ).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    staff.is_active = False
    db.commit()
    return {"message": "Staff deactivated"}