from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "hrms-backend"
    APP_NAME: str = "AI_HR_Backend"
    DEBUG: bool = False

    DATABASE_URL: str
    UPLOAD_DIR: str = "uploads"
    SECRET_KEY: str

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM: str

    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    SCORE_THRESHOLD: float = Field(default=25.0, description="From .env; restart server after changes")
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()