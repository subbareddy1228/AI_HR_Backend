from sqlalchemy import Column, Integer, String, Time, Boolean, DateTime
from core.database import Base
from datetime import datetime


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    shift_name = Column(String(100), unique=True, nullable=False)   # Morning | Evening | Night | General
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    break_duration_minutes = Column(Integer, default=30)
    grace_period_minutes = Column(Integer, default=10)             # late arrival tolerance
    working_hours = Column(Integer, nullable=False)                # total hours per day
    is_night_shift = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
