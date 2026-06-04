from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean
from core.database import Base
from datetime import datetime


class SavedReport(Base):
    __tablename__ = "saved_reports"

    id = Column(Integer, primary_key=True)
    report_name = Column(String(255), unique=True)
    report_type = Column(String(100))
    filters = Column(JSON, nullable=True)
    columns_selected = Column(JSON, nullable=True)
    created_by = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
