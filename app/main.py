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
    whatsapp,
    prescriptions
)

# Scheduler
from app.jobs.reminder_cron import start_scheduler


# =========================================================
# FastAPI App
# =========================================================
app = FastAPI(
    title=settings.APP_NAME,
    description="Clinic Growth Engine — Vedic Homoeopathic Clinic",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# =========================================================
# CORS Configuration
# =========================================================
# Example:
# ALLOWED_ORIGINS=http://localhost:3000,https://yourfrontend.com
#
# If not set, defaults to "*"
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
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(visits.router)
app.include_router(billing.router)
app.include_router(analytics.router)
app.include_router(reminders.router)
app.include_router(queue.router)
app.include_router(whatsapp.router)
app.include_router(prescriptions.router)


# =========================================================
# Startup Event
# =========================================================
@app.on_event("startup")
def startup():
    """
    Runs when FastAPI server starts
    """

    # Create all database tables
    create_tables()

    # Start APScheduler
    start_scheduler()

    print("✅ All tables created in Supabase")
    print("✅ Clinic Growth Engine running")
    print("✅ Scheduler started")


# =========================================================
# Root Endpoint
# =========================================================
@app.get("/")
def root():
    return {
        "status": "running",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }


# =========================================================
# Health Check
# =========================================================
@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }