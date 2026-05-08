from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "Vennova Clinic Growth Engine"
    DEBUG: bool = False
    PORT: int = 8000
    ENVIRONMENT: str = "production"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── Meta WhatsApp Cloud API ───────────────────────────────────────────────
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v19.0"

    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()