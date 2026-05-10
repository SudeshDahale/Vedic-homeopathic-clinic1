from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth_middleware import doctor_only
from app.models.user import User
from app.models.clinic import Clinic
import uuid, os

router = APIRouter(prefix="/uploads", tags=["Uploads"])

UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/signature")
async def upload_signature(
    file:         UploadFile = File(...),
    db:           Session    = Depends(get_db),
    current_user: User       = Depends(doctor_only)
):
    """Upload doctor signature image"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files allowed")
    
    ext      = file.filename.split(".")[-1]
    filename = f"sig_{current_user.clinic_id}.{ext}"
    path     = f"{UPLOAD_DIR}/{filename}"
    
    with open(path, "wb") as f:
        f.write(await file.read())
    
    # Save path to clinic
    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()
    if clinic:
        clinic.signature_url = path
        db.commit()
    
    return {"message": "Signature uploaded", "path": path}

@router.post("/logo")
async def upload_logo(
    file:         UploadFile = File(...),
    db:           Session    = Depends(get_db),
    current_user: User       = Depends(doctor_only)
):
    """Upload clinic logo"""
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "Only image files allowed")
    
    ext      = file.filename.split(".")[-1]
    filename = f"logo_{current_user.clinic_id}.{ext}"
    path     = f"{UPLOAD_DIR}/{filename}"
    
    with open(path, "wb") as f:
        f.write(await file.read())
    
    clinic = db.query(Clinic).filter(
        Clinic.id == current_user.clinic_id
    ).first()
    if clinic:
        clinic.logo_url = path
        db.commit()
    
    return {"message": "Logo uploaded", "path": path}