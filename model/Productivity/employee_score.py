from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import date
from core.database import Base


class EmployeeProductivity(Base):
    __tablename__ = "employee_productivity"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)

    date = Column(Date, nullable=False, default=date.today, server_default=func.current_date())
    period = Column(String(20), nullable=False)

    overall_score = Column(Float, default=0.0, nullable=False)
    activity_score = Column(Float, default=0.0, nullable=True)
    task_score = Column(Float, default=0.0, nullable=True)
    okr_score = Column(Float, default=0.0, nullable=True)
    time_score = Column(Float, default=0.0, nullable=True)

    tasks_completed = Column(Integer, default=0)
    hours_logged = Column(Float, default=0.0)
    active_time_seconds = Column(Integer, default=0)

    summary = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee = relationship("Employee", back_populates="employee_productivity")
    department = relationship("Department", back_populates="employee_productivity")
    team = relationship("Team", back_populates="employee_productivity")
