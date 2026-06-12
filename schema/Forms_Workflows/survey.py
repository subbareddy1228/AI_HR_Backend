

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from model.Forms_Workflows.survey import (
    BSCPerspective,
    DistributionMethod,
    QuestionType,
    RecurringFrequency,
    ScheduleType,
    SurveyStatus,
    TargetAudienceType,
    TemplateCategory,
    VisibilityMode,
)

class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class QuestionBankCreate(_Base):
    question:    str
    type:        QuestionType = QuestionType.RATING
    category:    Optional[str] = None
    perspective: BSCPerspective = BSCPerspective.GENERAL
    tags:        Optional[List[str]] = Field(default_factory=list)
    options:     Optional[List[str]] = None
    scale_min:   Optional[int] = Field(default=1, ge=1)
    scale_max:   Optional[int] = Field(default=5, le=10)

    @model_validator(mode="after")
    def validate_options_for_type(self) -> "QuestionBankCreate":
        if self.type in (QuestionType.MULTIPLE, QuestionType.RANKING) and not self.options:
            raise ValueError(f"'options' is required for question type '{self.type}'")
        return self


class QuestionBankUpdate(_Base):
    question:    Optional[str] = None
    type:        Optional[QuestionType] = None
    category:    Optional[str] = None
    perspective: Optional[BSCPerspective] = None
    tags:        Optional[List[str]] = None
    options:     Optional[List[str]] = None
    scale_min:   Optional[int] = None
    scale_max:   Optional[int] = None
    is_active:   Optional[bool] = None


class QuestionBankResponse(_Base):
    id:          int
    question:    str
    type:        str
    category:    Optional[str]
    perspective: str
    tags:        Optional[List[str]]
    options:     Optional[List[str]]
    scale_min:   Optional[int]
    scale_max:   Optional[int]
    times_used:  int
    last_used:   Optional[datetime]
    is_active:   bool
    created_by:  Optional[str]
    created_at:  datetime


class QuestionBankListResponse(_Base):

    items:       List[QuestionBankResponse]
    total:       int
    page:        int
    page_size:   int


class SurveyQuestionCreate(_Base):
    question_text:    str
    type:             QuestionType = QuestionType.RATING
    category:         Optional[str] = None
    perspective:      BSCPerspective = BSCPerspective.GENERAL
    options:          Optional[List[str]] = None
    scale_min:        Optional[int] = Field(default=1, ge=1)
    scale_max:        Optional[int] = Field(default=5, le=10)
    is_required:      bool = True
    order_index:      int = 0
    skip_logic:       Optional[List[Dict[str, Any]]] = None
    bank_question_id: Optional[int] = None   # link to question bank

    @model_validator(mode="after")
    def validate_options(self) -> "SurveyQuestionCreate":
        if self.type in (QuestionType.MULTIPLE, QuestionType.RANKING) and not self.options:
            raise ValueError(f"'options' required for type '{self.type}'")
        return self


class SurveyQuestionUpdate(_Base):
    question_text: Optional[str] = None
    type:          Optional[QuestionType] = None
    category:      Optional[str] = None
    perspective:   Optional[BSCPerspective] = None
    options:       Optional[List[str]] = None
    scale_min:     Optional[int] = None
    scale_max:     Optional[int] = None
    is_required:   Optional[bool] = None
    order_index:   Optional[int] = None
    skip_logic:    Optional[List[Dict[str, Any]]] = None


class SurveyQuestionResponse(_Base):
    id:               int
    survey_id:        int
    bank_question_id: Optional[int]
    question_text:    str
    type:             str
    category:         Optional[str]
    perspective:      str
    options:          Optional[List[str]]
    scale_min:        Optional[int]
    scale_max:        Optional[int]
    is_required:      bool
    order_index:      int
    skip_logic:       Optional[List[Dict[str, Any]]]
    created_at:       datetime


class SurveyCreate(_Base):
    title:               str                           = Field(..., min_length=3, max_length=255)
    description:         Optional[str]                 = None
    bsc_perspective:     BSCPerspective                = BSCPerspective.ALL
    strategic_alignment: Optional[List[str]]           = None
    visibility_mode:     VisibilityMode                = VisibilityMode.ANONYMOUS
    start_date:          Optional[datetime]             = None
    end_date:            Optional[datetime]             = None
    expiry_days:         Optional[int]                  = Field(default=7, ge=1, le=365)
    enable_skip_logic:   bool                           = True
    randomize_questions: bool                           = False
    show_progress_bar:   bool                           = True
    completion_message:  Optional[str]                  = "Show Thank you message"
    reminder_settings:   Optional[str]                  = "Send 2 reminders"
    template_id:         Optional[int]                  = None
    questions:           Optional[List[SurveyQuestionCreate]] = Field(default_factory=list)

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v: Optional[datetime], info: Any) -> Optional[datetime]:
        start = info.data.get("start_date")
        if v and start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v


class SurveyUpdate(_Base):
    title:               Optional[str]                  = Field(default=None, min_length=3, max_length=255)
    description:         Optional[str]                  = None
    bsc_perspective:     Optional[BSCPerspective]       = None
    strategic_alignment: Optional[List[str]]            = None
    visibility_mode:     Optional[VisibilityMode]       = None
    status:              Optional[SurveyStatus]         = None
    start_date:          Optional[datetime]             = None
    end_date:            Optional[datetime]             = None
    expiry_days:         Optional[int]                  = None
    enable_skip_logic:   Optional[bool]                 = None
    randomize_questions: Optional[bool]                 = None
    show_progress_bar:   Optional[bool]                 = None
    completion_message:  Optional[str]                  = None
    reminder_settings:   Optional[str]                  = None


class SurveyResponse(_Base):
    id:                  int
    title:               str
    description:         Optional[str]
    bsc_perspective:     str
    strategic_alignment: Optional[List[str]]
    visibility_mode:     str
    status:              str
    start_date:          Optional[datetime]
    end_date:            Optional[datetime]
    expiry_days:         Optional[int]
    enable_skip_logic:   bool
    randomize_questions: bool
    show_progress_bar:   bool
    completion_message:  Optional[str]
    reminder_settings:   Optional[str]
    template_id:         Optional[int]
    created_by:          Optional[str]
    created_at:          datetime
    updated_at:          Optional[datetime]
    questions:           List[SurveyQuestionResponse] = Field(default_factory=list)


class SurveyListItem(_Base):

    id:          int
    title:       str
    status:      str
    perspective: str
    questions:   int   # count
    responses:   int   # count
    created_at:  datetime



class DistributionCreate(_Base):
    methods:             List[DistributionMethod]  = Field(..., min_length=1)
    schedule_type:       ScheduleType              = ScheduleType.SEND_IMMEDIATELY
    scheduled_at:        Optional[datetime]         = None
    recurring_frequency: Optional[RecurringFrequency] = None
    recurring_end_date:  Optional[datetime]         = None
    event_trigger:       Optional[str]              = None
    audience_type:       TargetAudienceType         = TargetAudienceType.ALL_EMPLOYEES
    audience_filter:     Optional[Dict[str, Any]]   = None
    max_reminders:       Optional[int]               = Field(default=3, ge=0, le=10)

    @model_validator(mode="after")
    def validate_schedule(self) -> "DistributionCreate":
        if self.schedule_type == ScheduleType.SCHEDULE_LATER and not self.scheduled_at:
            raise ValueError("'scheduled_at' required when schedule_type is SCHEDULE_LATER")
        if self.schedule_type == ScheduleType.RECURRING and not self.recurring_frequency:
            raise ValueError("'recurring_frequency' required when schedule_type is RECURRING")
        if self.schedule_type == ScheduleType.EVENT_TRIGGERED and not self.event_trigger:
            raise ValueError("'event_trigger' required when schedule_type is EVENT_TRIGGERED")
        return self


class DistributionUpdate(_Base):
    methods:             Optional[List[DistributionMethod]] = None
    schedule_type:       Optional[ScheduleType]             = None
    scheduled_at:        Optional[datetime]                  = None
    recurring_frequency: Optional[RecurringFrequency]       = None
    recurring_end_date:  Optional[datetime]                  = None
    event_trigger:       Optional[str]                       = None
    audience_type:       Optional[TargetAudienceType]        = None
    audience_filter:     Optional[Dict[str, Any]]            = None
    max_reminders:       Optional[int]                        = None


class DistributionResponse(_Base):
    id:                  int
    survey_id:           int
    methods:             List[str]
    schedule_type:       str
    scheduled_at:        Optional[datetime]
    recurring_frequency: Optional[str]
    recurring_end_date:  Optional[datetime]
    event_trigger:       Optional[str]
    audience_type:       str
    audience_filter:     Optional[Dict[str, Any]]
    total_recipients:    int
    max_reminders:       int
    # Participation tracking
    emails_sent:         int
    emails_opened:       int
    surveys_started:     int
    surveys_completed:   int
    surveys_in_progress: int
    surveys_not_started: int
    reminders_sent:      int
    shareable_link:      Optional[str]
    launched_at:         Optional[datetime]
    last_reminder_at:    Optional[datetime]
    created_at:          datetime
    updated_at:          Optional[datetime]


class LaunchSurveyRequest(_Base):

    distribution: DistributionCreate


class AnswerItem(_Base):
    question_id: int
    answer:      Union[str, int, float, List[str], None]
    score:       Optional[float] = None


class SurveySubmitRequest(_Base):
    employee_id:  Optional[int]  = None   
    answers:      List[AnswerItem]
    nps_score:    Optional[int]   = Field(default=None, ge=0, le=10)
    is_anonymous: bool            = False


class SurveySubmitResponse(_Base):
    id:           int
    survey_id:    int
    employee_id:  Optional[int]
    is_complete:  bool
    submitted_at: Optional[datetime]


class DepartmentComparison(_Base):
    department:         str
    response_rate:      float  
    satisfaction_score: float
    trend:              Optional[str] = None  


class TrendPoint(_Base):
    period_label: str
    score:        float


class SentimentBreakdown(_Base):
    positive_pct: float
    neutral_pct:  float
    negative_pct: float
    word_cloud:   List[Dict[str, Any]] = Field(default_factory=list)


class SurveyAnalyticsResponse(_Base):
    id:                   int
    survey_id:            int
    total_recipients:     int
    total_responses:      int
    response_rate:        float
    completion_rate:      float
    average_nps_score:    Optional[float]
    avg_satisfaction:     Optional[float]
    department_comparison: List[DepartmentComparison]
    trend_data:           List[TrendPoint]
    sentiment_data:       SentimentBreakdown
    question_results:     List[Dict[str, Any]]
    refreshed_at:         Optional[datetime]


class RefreshAnalyticsResponse(_Base):
    message:      str
    refreshed_at: datetime


class TemplateResponse(_Base):
    id:              int
    title:           str
    description:     Optional[str]
    category:        str
    perspective:     str
    questions_count: int
    estimated_min:   Optional[int]
    frequency_label: Optional[str]
    template_data:   Dict[str, Any]
    is_active:       bool
    created_at:      datetime


class UseTemplateRequest(_Base):

    title:       str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None


class AddQuestionsFromBankRequest(_Base):
    bank_question_ids: List[int] = Field(..., min_length=1)


class ReorderQuestionsRequest(_Base):

    order: Dict[int, int]


class SendRemindersResponse(_Base):
    survey_id:       int
    reminders_sent:  int
    recipients:      int
    message:         str
