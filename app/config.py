from pydantic_settings import BaseSettings
from functools import lru_cache
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):

    # ─────────────────────────────────────────
    # APP
    # ─────────────────────────────────────────
    APP_NAME: str = "Vennova Clinic Growth Engine"
    DEBUG: bool = False
    PORT: int = 8000
    ENVIRONMENT: str = "production"

    # ─────────────────────────────────────────
    # DATABASE
    # ─────────────────────────────────────────
    DATABASE_URL: str

    # ─────────────────────────────────────────
    # SUPABASE
    # ─────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ─────────────────────────────────────────
    # AUTH
    # ─────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ─────────────────────────────────────────
    # WHATSAPP
    # ─────────────────────────────────────────
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v19.0"

    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""

    # ─────────────────────────────────────────
    # CORS
    # ─────────────────────────────────────────
    ALLOWED_ORIGINS: str = "*"

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()