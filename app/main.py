from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.routers import analytics, auth
from app.routers.patients import router as patient_router
from app.jobs.reminder_cron import start_scheduler

app = FastAPI(
    title=settings.APP_NAME,
    description="Clinic Growth Engine — Vedic Homoeopathic Clinic",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(patient_router)

@app.on_event("startup")
def startup():
    create_tables()
    start_scheduler()
    print("✅ All tables created in Supabase")
    print("✅ Clinic Growth Engine running")

@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}