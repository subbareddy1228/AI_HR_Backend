from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime


# ── Survey schemas ─────────────────────────────────────────────────────────────

class SurveyBase(BaseModel):
    title: str
    description: Optional[str] = None
    survey_type: str
    questions: Optional[Any] = None
    is_active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_by: Optional[str] = None


class SurveyCreate(SurveyBase):
    pass


class SurveyUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    survey_type: Optional[str] = None
    questions: Optional[Any] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class SurveyResponse(SurveyBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── SurveyResponse schemas ─────────────────────────────────────────────────────

class SurveyResponseBase(BaseModel):
    survey_id: int
    employee_id: Optional[int] = None
    responses: Optional[Any] = None
    is_anonymous: bool = False


class SurveyResponseCreate(SurveyResponseBase):
    pass


class SurveyResponseResponse(SurveyResponseBase):
    id: int
    submitted_at: datetime
    model_config = ConfigDict(from_attributes=True)
