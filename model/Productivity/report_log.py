# app/models/report_log.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey,func
from sqlalchemy.orm import relationship
from app.core.database import Base
# ReportLog Model
class ReportLog(Base):
    __tablename__ = "report_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(100), nullable=False)
    generated_by = Column(Integer, ForeignKey("employee.id", ondelete="SET NULL"), nullable=True)
    file_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    generator = relationship("Employee", backref="generated_reports", foreign_keys=[generated_by])
