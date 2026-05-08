from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str      = "Vennova Clinic Growth Engine"
    DEBUG: bool        = False
    PORT: int          = 8000
    ENVIRONMENT: str   = "production"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str
    SUPABASE_URL: str  = ""
    SUPABASE_KEY: str  = ""        # anon/service key for Storage uploads

    # ── Auth ──────────────────────────────────────────────────────────────────
    JWT_SECRET: str
    JWT_ALGORITHM: str     = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # ── Meta WhatsApp Cloud API ───────────────────────────────────────────────
    WHATSAPP_API_URL: str          = "https://graph.facebook.com/v19.0"
    WHATSAPP_PHONE_NUMBER_ID: str  = "1079990315201370"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = "809296841946428"
    WHATSAPP_ACCESS_TOKEN: str     = "EAANjub6OabwBRQMZCCikfYSQMmepLWwekfXuk9AU6DY9Na2Ow4AGTlaOdw0T7PprtQFfiHGZC7Y6GQib5IXn1ADNdZA6KdZC46ICKzwEZBryyJsGuLnhKCV5lxla9v4mjWiaWiikLqAUCgGasF0cwk8lpHxNWONI99a4D816orqAyrdSg5xPWZCOfyJZBC7fWQp6AZDZD"
    WHATSAPP_VERIFY_TOKEN: str     = "vennova_webhook_verify_2026"

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "*"     # set to Lovable URL in production

    class Config:
        env_file = ".env"
        extra    = "allow"         # ignores unknown env vars gracefully


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()