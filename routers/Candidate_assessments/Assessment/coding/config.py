from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Add Backend directory to path to import core.database
backend_dir = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from core.database import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    # Use main app's database configuration
    DB_HOST = POSTGRES_HOST
    DB_PORT = int(POSTGRES_PORT)
    DB_NAME = POSTGRES_DB
    DB_USER = POSTGRES_USER
    DB_PASS = POSTGRES_PASSWORD
except ImportError:
    # Fallback to .env if core.database is not available
    load_dotenv()
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "4649")

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# OpenAI client setup
import openai
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = openai
openai_client.api_key = OPENAI_API_KEY
