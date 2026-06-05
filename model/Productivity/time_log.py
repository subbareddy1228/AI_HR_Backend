from sqlalchemy import Column, Integer, String, Float, DateTime
from core.database import Base
from datetime import datetime


class TimeLog(Base):
    __tablename__ = "productivity_time_logs"

    id          = Column(Integer, primary_key=True, index=True)
    employee    = Column(String(255), nullable=False)
    project     = Column(String(255), nullable=False)
    task        = Column(String(500), nullable=False)
    hours       = Column(Float, nullable=False)
    log_date    = Column(String(20), nullable=False)   # ISO date string  e.g. "2025-06-04"
    created_at  = Column(DateTime, default=datetime.utcnow)
