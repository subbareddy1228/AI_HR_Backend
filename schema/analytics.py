from pydantic import BaseModel
from typing import Optional
from datetime import date


class StageSummary(BaseModel):
    stage: Optional[str]
    count: int
    total_value: float

    model_config = {"from_attributes": True}

class SourceBreakdown(BaseModel):
    source: Optional[str]
    count: int
    percentage: float

    model_config = {"from_attributes": True}

class CompanyMonthSummary(BaseModel):
    month: str
    count: int

    model_config = {"from_attributes": True}

class ActivityTypeSummary(BaseModel):
    type: Optional[str]
    count: int

    model_config = {"from_attributes": True}
