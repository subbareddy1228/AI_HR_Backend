from pydantic import BaseModel
from typing import Optional
from datetime import date


# DEALS ANALYTICS SCHEMAS
class StageSummary(BaseModel):
    stage: Optional[str]
    count: int
    total_value: float

    model_config = {"from_attributes": True}

# LEADS ANALYTICS SCHEMAS
class SourceBreakdown(BaseModel):
    source: Optional[str]
    count: int
    percentage: float

    model_config = {"from_attributes": True}

# COMPANIES ANALYTICS
class CompanyMonthSummary(BaseModel):
    month: str
    count: int

    model_config = {"from_attributes": True}

# ACTIVITIES ANALYTICS
class ActivityTypeSummary(BaseModel):
    type: Optional[str]
    count: int

    model_config = {"from_attributes": True}
