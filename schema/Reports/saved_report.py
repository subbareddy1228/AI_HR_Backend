# schema/Reports/saved_report.py
# Schemas for ReportFeature and SavedReport

from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime
from model.Reports.saved_report import FeatureStatus, FeatureCategory


# ── ReportFeature Schemas ──────────────────────────────────────────────────────

class ReportFeatureBase(BaseModel):
    feature_name: str
    description:  Optional[str]            = None
    icon:         Optional[str]            = None
    category:     FeatureCategory          = FeatureCategory.builder
    status:       FeatureStatus            = FeatureStatus.published
    created_by:   Optional[str]            = None


class ReportFeatureCreate(ReportFeatureBase):
    pass


class ReportFeatureUpdate(BaseModel):
    feature_name: Optional[str]            = None
    description:  Optional[str]            = None
    icon:         Optional[str]            = None
    category:     Optional[FeatureCategory] = None
    status:       Optional[FeatureStatus]  = None


class ReportFeatureResponse(ReportFeatureBase):
    id:         int
    is_active:  bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── SavedReport Schemas ────────────────────────────────────────────────────────

class SavedReportBase(BaseModel):
    report_name:      str
    report_type:      str
    filters:          Optional[Any] = None
    columns_selected: Optional[Any] = None
    created_by:       Optional[str] = None


class SavedReportCreate(SavedReportBase):
    pass


class SavedReportUpdate(BaseModel):
    report_name:      Optional[str] = None
    report_type:      Optional[str] = None
    filters:          Optional[Any] = None
    columns_selected: Optional[Any] = None


class SavedReportResponse(SavedReportBase):
    id:         int
    is_active:  bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
