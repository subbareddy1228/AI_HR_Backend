from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class EmployeeProductivity(Base):
    __tablename__ = "employee_productivity"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    score = Column(Float, nullable=True)
    period = Column(String(50), nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    employee = relationship("Employee", foreign_keys=[employee_id])