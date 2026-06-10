
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from model.Reports.dashboard_metric import MetricStatus, MetricCategory


class DashboardMetricBase(BaseModel):
    metric_name: str
    category:    MetricCategory
    status:      MetricStatus
    value:       Optional[str] = None
    notes:       Optional[str] = None
    created_by:  Optional[str] = None


class DashboardMetricCreate(DashboardMetricBase):
    pass


class DashboardMetricUpdate(BaseModel):
    metric_name: Optional[str]             = None
    category:    Optional[MetricCategory]  = None
    status:      Optional[MetricStatus]    = None
    value:       Optional[str]             = None
    notes:       Optional[str]             = None


class DashboardMetricResponse(DashboardMetricBase):
    id:           int
    is_active:    bool
    last_updated: datetime

    model_config = ConfigDict(from_attributes=True)
