import os

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

from app.database import create_tables


# =========================================================
# ROUTERS
# =========================================================

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
from app.routers.health import (
    router as health_router
)

# WhatsApp Routers
from app.routers.whatsapp import (

    router as webhook_router,

    send_router as whatsapp_send_router
)

# Scheduler
from app.jobs.reminder_cron import (
    start_scheduler
)
from app.routers.billing_subscription import router as subscription_router

# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(

    title="Vennova Clinic Growth Engine API",

    description=(
        "AI-powered clinic growth "
        "operating system for modern clinics"
    ),

    version="2.0.0",

    docs_url="/docs",

    redoc_url="/redoc"
)


# =========================================================
# CORS CONFIGURATION
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
# INCLUDE ROUTERS
# =========================================================

# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

app.include_router(
    auth.router
)

# ---------------------------------------------------------
# PATIENTS
# ---------------------------------------------------------

app.include_router(
    patients.router
)

# ---------------------------------------------------------
# VISITS / CONSULTATIONS
# ---------------------------------------------------------

app.include_router(
    visits.router
)

# ---------------------------------------------------------
# BILLING / PAYMENTS
# ---------------------------------------------------------

app.include_router(
    billing.router
)

# ---------------------------------------------------------
# ANALYTICS
# ---------------------------------------------------------

app.include_router(
    analytics.router
)

# ---------------------------------------------------------
# FOLLOWUPS / REMINDERS
# ---------------------------------------------------------

app.include_router(
    reminders.router
)

# ---------------------------------------------------------
# QUEUE
# ---------------------------------------------------------

app.include_router(
    queue.router
)

# ---------------------------------------------------------
# WHATSAPP
# ---------------------------------------------------------

# GET  /webhooks/whatsapp
# POST /webhooks/whatsapp

app.include_router(
    webhook_router
)

# POST /whatsapp/send/message
# POST /whatsapp/send/reminder
# POST /whatsapp/send/thankyou/{id}
# POST /whatsapp/send/birthday/{id}

app.include_router(
    whatsapp_send_router
)

# ---------------------------------------------------------
# PRESCRIPTIONS
# ---------------------------------------------------------

app.include_router(
    prescriptions.router
)

# ---------------------------------------------------------
# STAFF MANAGEMENT
# ---------------------------------------------------------

app.include_router(
    staff.router
)

# ---------------------------------------------------------
# APPOINTMENTS
# ---------------------------------------------------------

app.include_router(
    appointments.router
)

# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------

app.include_router(
    imports.router
)

# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

app.include_router(
    health_router
)

app.include_router(subscription_router) 
# =========================================================
# STARTUP EVENT
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
# ROOT ENDPOINT
# =========================================================

@app.get("/")
def root():

    return {

        "app":
            "Vennova Clinic Growth Engine",

        "version":
            "2.0.0",

        "status":
            "running",

        "docs":
            "/docs"
    }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {

        "status":
            "healthy",

        "app":
            "Vennova",

        "version":
            "2.0.0"
    }


# =========================================================
# PRIVACY POLICY
# =========================================================

@app.get("/privacy-policy")
def privacy_policy():
    """
    Meta required privacy policy endpoint.
    """

    return {

        "app":
            "Vennova",

        "message":
            (
                "Vennova respects user privacy "
                "and securely stores clinic data. "
                "Users may contact support for "
                "data-related requests."
            )
    }


# =========================================================
# TERMS & CONDITIONS
# =========================================================

@app.get("/terms")
def terms():
    """
    Meta required terms endpoint.
    """

    return {

        "app":
            "Vennova",

        "message":
            (
                "By using Vennova, users agree "
                "to use the platform responsibly "
                "for clinic management and "
                "patient communication purposes."
            )
    }


# =========================================================
# DELETE USER DATA
# =========================================================

@app.get("/delete-data")
def delete_data():
    """
    Meta required data deletion endpoint.
    """

    return {

        "app":
            "Vennova",

        "message":
            (
                "To request deletion of account "
                "or patient data, contact support."
            )
    }