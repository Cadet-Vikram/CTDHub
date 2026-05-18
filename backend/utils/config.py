"""App configuration via environment variables / .env"""

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME:   str   = "Connecting the Dots"
    DEBUG:      bool  = True
    DATABASE_URL: str = "sqlite+aiosqlite:///./connecting_dots.db"
    SECRET_KEY: str   = "change-in-production"
    SIMILARITY_THRESHOLD: float = 0.60
    UPLOAD_DIR: str   = "uploads"

    # Optional integrations
    TWILIO_ACCOUNT_SID:  Optional[str] = None
    TWILIO_AUTH_TOKEN:   Optional[str] = None
    TWILIO_PHONE:        Optional[str] = None
    FIREBASE_CRED_PATH:  Optional[str] = None

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
