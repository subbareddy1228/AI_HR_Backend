from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional
from decimal import Decimal


class PromotionCreate(BaseModel):
    employee_id: int
    from_designation: str
    to_designation: str
    from_grade: Optional[str] = None
    to_grade: Optional[str] = None
    effective_date: date
    revised_salary: Optional[Decimal] = None
    reason: Optional[str] = None


class PromotionUpdate(BaseModel):
    status: Optional[str] = None    
    approved_by: Optional[int] = None
    revised_salary: Optional[Decimal] = None
    remarks: Optional[str] = None


class PromotionResponse(BaseModel):
    id: int
    employee_id: int
    from_designation: str
    to_designation: str
    from_grade: Optional[str]
    to_grade: Optional[str]
    effective_date: date
    revised_salary: Optional[Decimal]
    reason: Optional[str]
    status: str
    approved_by: Optional[int]
    remarks: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
