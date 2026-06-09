from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.database import Base

class ReportLog(Base):
    __tablename__ = "report_logs"

    id = Column(Integer, primary_key=True, index=True)
    generated_by = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    report_type = Column(String(100), nullable=True)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    generator = relationship("Employee", foreign_keys=[generated_by])