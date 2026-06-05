# model/Reports/saved_report.py
# Models: ReportFeature, SavedReport
# Tables: report_features, saved_reports

from sqlalchemy import Column, Integer, String, JSON, DateTime, Boolean, Text, Enum as SAEnum
from core.database import Base
from datetime import datetime
import enum


# ── Enums ──────────────────────────────────────────────────────────────────────

class FeatureStatus(str, enum.Enum):
    published   = "Published"
    in_progress = "In Progress"
    scheduled   = "Scheduled"


class FeatureCategory(str, enum.Enum):
    builder  = "Builder"
    data     = "Data"
    filter   = "Filter"
    analysis = "Analysis"
    template = "Template"
    export   = "Export"
    sharing  = "Sharing"


# ── ReportFeature ──────────────────────────────────────────────────────────────
# Drives the main table in the screenshot:
# Icon | Feature Name | Category | Last Updated | Status | Actions

class ReportFeature(Base):
    __tablename__ = "report_features"

    id           = Column(Integer, primary_key=True, index=True)
    feature_name = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    icon         = Column(String(100), nullable=True)       # icon identifier
    category     = Column(
                       SAEnum(FeatureCategory, name="feature_category_enum"),
                       nullable=False,
                       default=FeatureCategory.builder,
                   )
    status       = Column(
                       SAEnum(FeatureStatus, name="feature_status_enum"),
                       nullable=False,
                       default=FeatureStatus.published,
                   )
    is_active    = Column(Boolean, default=True)
    created_by   = Column(String(100), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── SavedReport ────────────────────────────────────────────────────────────────
# Stores user-built report configurations (filters, columns, data source)

class SavedReport(Base):
    __tablename__ = "saved_reports"

    id               = Column(Integer, primary_key=True, index=True)
    report_name      = Column(String(255), unique=True, nullable=False)
    report_type      = Column(String(100), nullable=False)  # Employee/Attendance/Payroll/Leave
    filters          = Column(JSON, nullable=True)
    columns_selected = Column(JSON, nullable=True)
    created_by       = Column(String(100), nullable=True)
    is_active        = Column(Boolean, default=True)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
