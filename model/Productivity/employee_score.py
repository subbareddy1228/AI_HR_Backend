from sqlalchemy import Column, Integer, String, Float, DateTime
from core.database import Base
from datetime import datetime


class EmployeeProductivity(Base):
    __tablename__ = "productivity_employee_scores"

    id              = Column(Integer, primary_key=True, index=True)
    employee_name   = Column(String(255), nullable=False)
    department      = Column(String(100), nullable=True)
    role            = Column(String(255), nullable=True)
    score           = Column(Integer, default=0)          # 0-100
    tasks_assigned  = Column(Integer, default=0)
    tasks_completed = Column(Integer, default=0)
    avg_hours       = Column(Float, default=0)
    streak_days     = Column(Integer, default=0)
    trend           = Column(String(20), nullable=True)   # e.g. "+5%"
    status          = Column(String(30), default="good")  # excellent / good / needs-improvement
    period          = Column(String(30), nullable=True)   # "2025-06" for monthly snapshots
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
