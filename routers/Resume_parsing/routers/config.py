import os
from dotenv import load_dotenv

load_dotenv()

def require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val

# REQUIRED
OPENAI_API_KEY = require_env("OPENAI_API_KEY")
DATABASE_URL   = require_env("DATABASE_URL")

# SMTP — USE CENTRAL NAMING
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_USERNAME = require_env("SMTP_USERNAME")
SMTP_PASSWORD = require_env("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)

SCORE_THRESHOLD = float(require_env("SCORE_THRESHOLD"))

print("[CONFIG] Resume parsing config loaded successfully")
print(f"[CONFIG] SMTP_HOST={SMTP_HOST}, SMTP_PORT={SMTP_PORT}")
print(f"[CONFIG] SCORE_THRESHOLD={SCORE_THRESHOLD}")
