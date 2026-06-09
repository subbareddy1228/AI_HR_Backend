from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class TimeLog(Base):
    __tablename__ = "time_logs"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("productivity_tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("productivity_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    hours = Column(Float, nullable=True)
    date = Column(DateTime(timezone=True), server_default=func.now())
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])
    task = relationship("ProductivityTask", foreign_keys=[task_id])