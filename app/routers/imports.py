from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.middleware.auth_middleware import doctor_only, receptionist_or_doctor
from app.models.import_job import ImportJob
from app.models.user import User
from app.enums import ImportStatus
import uuid, os, json

router = APIRouter(prefix="/imports", tags=["Patient Import"])

async def _process_csv(db: Session, job_id: str,
                       clinic_id: str, file_path: str):
    """Background task — process CSV file"""
    import csv
    from app.models.patient import Patient
    from app.services.patient_service import get_next_reg_no

    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job:
        return

    job.status = ImportStatus.PROCESSING
    db.commit()

    errors    = []
    success   = 0
    failed    = 0

    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader   = csv.DictReader(f)
            rows     = list(reader)
            job.total_rows = len(rows)
            db.commit()

            for i, row in enumerate(rows):
                try:
                    # Normalize column names (case-insensitive)
                    row = {k.strip().lower(): v.strip() for k, v in row.items()}

                    first_name = row.get("first_name") or row.get("name", "").split()[0]
                    if not first_name:
                        raise ValueError("First name required")

                    # Check duplicate by phone
                    phone = row.get("phone") or row.get("mobile") or row.get("phone_mobile")
                    if phone:
                        existing = db.query(Patient).filter(
                            Patient.clinic_id    == clinic_id,
                            Patient.phone_mobile == phone
                        ).first()
                        if existing:
                            errors.append({"row": i+2, "reason": f"Duplicate phone: {phone}"})
                            failed += 1
                            continue

                    patient = Patient(
                        clinic_id    = clinic_id,
                        reg_no       = get_next_reg_no(db, clinic_id),
                        first_name   = first_name,
                        last_name    = row.get("last_name", ""),
                        phone_mobile = phone,
                        email        = row.get("email"),
                        res_city     = row.get("city"),
                        res_state    = row.get("state"),
                        patient_type = row.get("patient_type", "HOMEOPATHY").upper()
                    )
                    db.add(patient)
                    success += 1

                    # Bulk commit every 50 rows
                    if i % 50 == 0:
                        db.commit()

                except Exception as e:
                    errors.append({"row": i+2, "reason": str(e)})
                    failed += 1

                job.processed_rows = i + 1
                db.commit()

        db.commit()

        job.status          = ImportStatus.COMPLETED
        job.successful_rows = success
        job.failed_rows     = failed
        job.error_log       = json.dumps(errors[:50])  # store first 50 errors

    except Exception as e:
        job.status    = ImportStatus.FAILED
        job.error_log = str(e)

    finally:
        job.completed_at = str(__import__("datetime").datetime.utcnow())
        db.commit()
        # Clean up temp file
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("/patients")
async def import_patients(
    background_tasks: BackgroundTasks,
    file:             UploadFile = File(...),
    db:               Session    = Depends(get_db),
    current_user:     User       = Depends(receptionist_or_doctor)
):
    """
    Import patients from CSV or Excel.
    Runs in background — returns job_id to track progress.
    
    CSV columns (flexible, case-insensitive):
    first_name, last_name, phone/mobile, email, city, state, patient_type
    """
    # Validate file type
    filename = file.filename.lower()
    if not any(filename.endswith(ext) for ext in [".csv", ".xlsx", ".xls"]):
        raise HTTPException(
            status_code=400,
            detail="Only CSV and Excel files supported"
        )

    file_type = "csv" if filename.endswith(".csv") else "excel"

    # Save to temp
    temp_path = f"/tmp/import_{uuid.uuid4()}{os.path.splitext(filename)[1]}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Convert Excel to CSV if needed
    if file_type == "excel":
        try:
            import pandas as pd
            df = pd.read_excel(temp_path)
            csv_path = temp_path.replace(".xlsx", ".csv").replace(".xls", ".csv")
            df.to_csv(csv_path, index=False)
            os.remove(temp_path)
            temp_path = csv_path
            file_type = "csv"
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read Excel: {e}")

    # Create import job
    job = ImportJob(
        clinic_id    = current_user.clinic_id,
        uploaded_by  = current_user.id,
        file_name    = file.filename,
        file_type    = file_type,
        status       = ImportStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Run in background
    background_tasks.add_task(
        _process_csv, db, job.id,
        current_user.clinic_id, temp_path
    )

    return {
        "message":  "Import started",
        "job_id":   job.id,
        "filename": file.filename,
        "note":     "Check /imports/{job_id}/status for progress"
    }

@router.get("/history")
def import_history(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """List all import jobs for this clinic"""
    jobs = db.query(ImportJob).filter(
        ImportJob.clinic_id == current_user.clinic_id
    ).order_by(ImportJob.created_at.desc()).limit(20).all()

    return {
        "jobs": [
            {
                "id":               j.id,
                "file_name":        j.file_name,
                "file_type":        j.file_type,
                "status":           j.status,
                "total_rows":       j.total_rows,
                "successful_rows":  j.successful_rows,
                "failed_rows":      j.failed_rows,
                "created_at":       j.created_at.strftime("%d-%m-%Y %H:%M") if j.created_at else None,
                "completed_at":     j.completed_at
            }
            for j in jobs
        ]
    }

@router.get("/{job_id}/status")
def import_status(
    job_id:       str,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(receptionist_or_doctor)
):
    """Check import job progress"""
    job = db.query(ImportJob).filter(
        ImportJob.id        == job_id,
        ImportJob.clinic_id == current_user.clinic_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    progress = 0
    if job.total_rows and job.total_rows > 0:
        progress = round((job.processed_rows / job.total_rows) * 100, 1)

    return {
        "job_id":          job.id,
        "status":          job.status,
        "file_name":       job.file_name,
        "total_rows":      job.total_rows,
        "processed_rows":  job.processed_rows,
        "successful_rows": job.successful_rows,
        "failed_rows":     job.failed_rows,
        "progress_pct":    progress,
        "errors":          json.loads(job.error_log) if job.error_log else []
    }