from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "hrms-backend"
    DEBUG: bool = False

    DATABASE_URL: str
    UPLOAD_DIR: str = "uploads"
    SECRET_KEY: str

    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    AWS_BUCKET_NAME: str = ""
    CLOUDFRONT_URL: str = ""
    ALGORITHM: str = "HS256"
    REDIS_URL: str = "redis://localhost:6379"

    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # Must match Backend/.env SCORE_THRESHOLD; resume screening logic uses
    # routers.Resume_parsing.routers.config.SCORE_THRESHOLD (required at import).
    SCORE_THRESHOLD: float = Field(default=25.0, description="From .env; restart server after changes")
    OPENAI_API_KEY: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()


#updated by subbu