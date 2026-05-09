import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

# Routers
from app.routers import (
    analytics,
    auth,
    patients,
    visits,
    billing,
    reminders,
    queue,
    prescriptions,
    staff,
    appointments,
    imports
)

# Health Router
from app.routers.health import router as health_router

# WhatsApp Routers (two separate routers in one file)
from app.routers.whatsapp import (
    router as webhook_router,
    send_router as whatsapp_send_router
)

# Scheduler
from app.jobs.reminder_cron import start_scheduler

# =========================================================
# FastAPI App
# =========================================================
app = FastAPI(
    title="Vennova Clinic Growth Engine API",
    description="AI-powered clinic growth operating system for modern clinics",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# =========================================================
# CORS Configuration
# =========================================================
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "*"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# Include Routers
# =========================================================

# Authentication
app.include_router(auth.router)

# Patients
app.include_router(patients.router)

# Visits / Consultations
app.include_router(visits.router)

# Billing / Payments
app.include_router(billing.router)

# Analytics
app.include_router(analytics.router)

# Followups / Reminders
app.include_router(reminders.router)

# Queue
app.include_router(queue.router)

# WhatsApp — webhook receiver + outbound send
app.include_router(webhook_router)        # GET /webhooks/whatsapp  (Meta verify)
                                          # POST /webhooks/whatsapp (incoming msgs)
app.include_router(whatsapp_send_router)  # POST /whatsapp/send/message
                                          # POST /whatsapp/send/reminder
                                          # POST /whatsapp/send/thankyou/{id}
                                          # POST /whatsapp/send/birthday/{id}

# Prescriptions
app.include_router(prescriptions.router)

# Staff Management
app.include_router(staff.router)

# Appointments
app.include_router(appointments.router)

# Imports
app.include_router(imports.router)

# Health Check
app.include_router(health_router)


# =========================================================
# Startup Event
# =========================================================
@app.on_event("startup")
def startup():
    """
    Runs when FastAPI server starts.
    """
    create_tables()
    start_scheduler()

    print("✅ Vennova v2.0 — All systems running")
    print("✅ Database tables initialized")
    print("✅ APScheduler started")
    print("✅ Supabase connected")
    print("✅ WhatsApp services active")


# =========================================================
# Root Endpoint
# =========================================================
@app.get("/")
def root():
    return {
        "app":     "Vennova Clinic Growth Engine",
        "version": "2.0.0",
        "status":  "running",
        "docs":    "/docs"
    }


# =========================================================
# Health Check
# =========================================================
@app.get("/health")
def health():
    return {
        "status":  "healthy",
        "app":     "Vennova",
        "version": "2.0.0"
    }