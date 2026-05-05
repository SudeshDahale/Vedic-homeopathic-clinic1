from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.routers import analytics
from app.jobs.reminder_cron import start_scheduler

app = FastAPI(
    title=settings.APP_NAME,
    description="Clinic Growth Engine — Vedic Homoeopathic Clinic",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS (for frontend later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(analytics.router)


# ✅ Startup event (CORRECT PLACE)
@app.on_event("startup")
def startup():
    create_tables()
    start_scheduler()   # 🔥 scheduler starts here (only once)
    print("✅ All tables created in Supabase")
    print("✅ Clinic Growth Engine running")
    print("✅ Scheduler started")


# Root route
@app.get("/")
def root():
    return {
        "status": "running",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }


# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}