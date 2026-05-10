from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,          # tests connection before using it
    pool_size=5,                 # reduced for free tier pooler
    max_overflow=10,
    pool_recycle=300,            # recycle every 5 min
    connect_args={
        "sslmode": "require",    # Supabase pooler requires SSL
        "connect_timeout": 10,   # fail fast instead of hanging
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from app.models.base import Base
    from app.models import clinic, user, patient, visit, billing, reminder
    Base.metadata.create_all(bind=engine)