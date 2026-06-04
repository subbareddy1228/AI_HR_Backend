from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


class SavedReportCreate(BaseModel):
    report_name: str
    report_type: str
    filters: Optional[Any] = None
    columns_selected: Optional[Any] = None
    created_by: Optional[str] = None


class SavedReportUpdate(BaseModel):
    report_name: Optional[str] = None
    report_type: Optional[str] = None
    filters: Optional[Any] = None
    columns_selected: Optional[Any] = None


class SavedReportResponse(SavedReportCreate):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    