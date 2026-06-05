# model/Reports/dashboard_metric.py
# Model: DashboardMetric
# Table: dashboard_metrics

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Enum as SAEnum
from core.database import Base
from datetime import datetime
import enum


class MetricStatus(str, enum.Enum):
    stable    = "Stable"
    alert     = "Alert"
    on_track  = "On Track"
    review    = "Review"
    normal    = "Normal"
    compliant = "Compliant"


class MetricCategory(str, enum.Enum):
    trend       = "Trend"
    analysis    = "Analysis"
    recruitment = "Recruitment"
    finance     = "Finance"
    attendance  = "Attendance"
    compliance  = "Compliance"


class DashboardMetric(Base):
    __tablename__ = "dashboard_metrics"

    id           = Column(Integer, primary_key=True, index=True)
    metric_name  = Column(String(255), nullable=False)
    category     = Column(SAEnum(MetricCategory, name="metric_category_enum"), nullable=False)
    status       = Column(SAEnum(MetricStatus,   name="metric_status_enum"),   nullable=False)
    value        = Column(String(100), nullable=True)   # e.g. "↑ 8.2%", "$4.2M", "78% filled"
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active    = Column(Boolean, default=True)
    created_by   = Column(String(100), nullable=True)
    notes        = Column(Text, nullable=True)
