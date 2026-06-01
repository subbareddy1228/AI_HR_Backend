# core/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from core.config import settings

# ----------------------------
# Database URL
# ----------------------------
DATABASE_URL = settings.DATABASE_URL

# ----------------------------
# Engine (SYNC ONLY)
# ----------------------------
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
)

# ----------------------------
# Base for ALL models
# ----------------------------
class Base(DeclarativeBase):
    pass

# ----------------------------
# Session maker (PURE SQLAlchemy)
# ----------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=Session,   # ✅ SQLAlchemy Session
)

# ----------------------------
# FastAPI Dependency
# ----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ----------------------------
# Initialize DB
# ----------------------------
def init_db():
    Base.metadata.create_all(bind=engine)
