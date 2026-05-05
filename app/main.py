from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for Vedic Homoeopathic Clinic — Clinic Growth Engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create all tables in Supabase on startup
@app.on_event("startup")
def startup():
    create_tables()
    print("✅ All tables created in Supabase")

@app.get("/")
def root():
    return {
        "status": "running",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}