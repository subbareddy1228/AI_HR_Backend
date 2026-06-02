from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from core.database import Base
from datetime import datetime


class WorkHourRule(Base):
    __tablename__ = "work_hour_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(255), unique=True, nullable=False)
    daily_hours = Column(Float, nullable=False, default=8.0)
    weekly_hours = Column(Float, nullable=False, default=40.0)
    overtime_threshold_daily = Column(Float, default=8.0)       # hours after which OT kicks in
    overtime_multiplier = Column(Float, default=1.5)            # 1.5x pay for OT
    work_days = Column(String(100), nullable=False, default="MON,TUE,WED,THU,FRI")  # comma-separated
    half_day_hours = Column(Float, default=4.0)
    min_hours_for_full_day = Column(Float, default=6.0)
    min_hours_for_half_day = Column(Float, default=3.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
