

from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Float, Enum as SAEnum, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
import enum

from core.database import Base


class SurveyStatus(str, enum.Enum):
    DRAFT     = "draft"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ARCHIVED  = "archived"


class VisibilityMode(str, enum.Enum):
    ANONYMOUS  = "anonymous"
    IDENTIFIED = "identified"


class QuestionType(str, enum.Enum):
    RATING   = "rating"
    MULTIPLE = "multiple"   
    OPEN     = "open"      
    NPS      = "nps"
    LIKERT   = "likert"
    BOOLEAN  = "boolean"
    RANKING  = "ranking"
    MATRIX   = "matrix"


class BSCPerspective(str, enum.Enum):
    ALL               = "All Perspectives"
    FINANCIAL         = "Financial"
    CUSTOMER          = "Customer"
    INTERNAL_PROCESS  = "Internal Process"
    LEARNING_GROWTH   = "Learning & Growth"
    GENERAL           = "General"


class DistributionMethod(str, enum.Enum):
    EMAIL           = "email"
    IN_APP          = "in_app"
    SMS             = "sms"
    QR_CODE         = "qr_code"
    SHAREABLE_LINK  = "shareable_link"


class ScheduleType(str, enum.Enum):
    SEND_IMMEDIATELY = "send_immediately"
    SCHEDULE_LATER   = "schedule_later"
    RECURRING        = "recurring"
    EVENT_TRIGGERED  = "event_triggered"


class RecurringFrequency(str, enum.Enum):
    DAILY      = "daily"
    WEEKLY     = "weekly"
    BI_WEEKLY  = "bi_weekly"
    MONTHLY    = "monthly"
    QUARTERLY  = "quarterly"


class TargetAudienceType(str, enum.Enum):
    ALL_EMPLOYEES  = "all_employees"
    BY_DEPARTMENT  = "by_department"
    BY_LOCATION    = "by_location"
    BY_ROLE        = "by_role"
    BY_TENURE      = "by_tenure"
    CUSTOM_GROUP   = "custom_group"


class TemplateCategory(str, enum.Enum):
    BALANCED_SCORECARD = "balanced_scorecard"
    STANDARD           = "standard"



class SurveyQuestionBank(Base):

    __tablename__ = "survey_question_bank"

    id          = Column(Integer, primary_key=True, index=True)
    question    = Column(Text, nullable=False)
    type        = Column(SAEnum(QuestionType), nullable=False, default=QuestionType.RATING)
    category    = Column(String(100), nullable=True)         
    perspective = Column(SAEnum(BSCPerspective), nullable=False, default=BSCPerspective.GENERAL)
    tags        = Column(JSON, nullable=True, default=list)   
    options     = Column(JSON, nullable=True)                 
    scale_min   = Column(Integer, nullable=True, default=1)   
    scale_max   = Column(Integer, nullable=True, default=5)
    times_used  = Column(Integer, nullable=False, default=0)
    last_used   = Column(DateTime, nullable=True)
    is_active   = Column(Boolean, default=True, nullable=False)
    created_by  = Column(String(100), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    survey_questions = relationship(
        "SurveyQuestion",
        back_populates="bank_question",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_sqb_type_perspective", "type", "perspective"),
        Index("ix_sqb_category", "category"),
    )



class SurveyTemplate(Base):

    __tablename__ = "survey_templates"

    id              = Column(Integer, primary_key=True, index=True)
    title           = Column(String(255), nullable=False)
    description     = Column(Text, nullable=True)
    category        = Column(SAEnum(TemplateCategory), nullable=False)
    perspective     = Column(SAEnum(BSCPerspective), nullable=False, default=BSCPerspective.GENERAL)
    questions_count = Column(Integer, nullable=False, default=0)
    estimated_min   = Column(Integer, nullable=True)           # completion time in minutes
    frequency_label = Column(String(50), nullable=True)        # "Monthly","Quarterly","On Exit"…
    template_data   = Column(JSON, nullable=False, default=dict)  # full question structure
    is_active       = Column(Boolean, default=True, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Survey(Base):

    __tablename__ = "surveys"

    id                  = Column(Integer, primary_key=True, index=True)
    title               = Column(String(255), nullable=False)
    description         = Column(Text, nullable=True)

    bsc_perspective     = Column(SAEnum(BSCPerspective), nullable=False, default=BSCPerspective.ALL)
    strategic_alignment = Column(JSON, nullable=True)          # list of aligned objective ids/labels

    visibility_mode     = Column(SAEnum(VisibilityMode), nullable=False, default=VisibilityMode.ANONYMOUS)

    status              = Column(SAEnum(SurveyStatus), nullable=False, default=SurveyStatus.DRAFT)

    start_date          = Column(DateTime, nullable=True)
    end_date            = Column(DateTime, nullable=True)
    expiry_days         = Column(Integer, nullable=True, default=7)

    enable_skip_logic   = Column(Boolean, default=True, nullable=False)
    randomize_questions = Column(Boolean, default=False, nullable=False)
    show_progress_bar   = Column(Boolean, default=True, nullable=False)
    completion_message  = Column(String(255), nullable=True, default="Show Thank you message")
    reminder_settings   = Column(String(100), nullable=True, default="Send 2 reminders")

    template_id         = Column(Integer, ForeignKey("survey_templates.id"), nullable=True)

    created_by          = Column(String(100), nullable=True)
    updated_by          = Column(String(100), nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    questions      = relationship(
        "SurveyQuestion",
        back_populates="survey",
        cascade="all, delete-orphan",
        order_by="SurveyQuestion.order_index",
    )
    distribution   = relationship(
        "SurveyDistribution",
        back_populates="survey",
        uselist=False,
        cascade="all, delete-orphan",
    )
    responses      = relationship(
        "SurveyResponse",
        back_populates="survey",
        cascade="all, delete-orphan",
    )
    analytics      = relationship(
        "SurveyAnalytics",
        back_populates="survey",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_surveys_status", "status"),
        Index("ix_surveys_bsc_perspective", "bsc_perspective"),
        Index("ix_surveys_created_at", "created_at"),
    )


class SurveyQuestion(Base):

    __tablename__ = "survey_questions"

    id              = Column(Integer, primary_key=True, index=True)
    survey_id       = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    bank_question_id = Column(Integer, ForeignKey("survey_question_bank.id"), nullable=True)

    question_text   = Column(Text, nullable=False)
    type            = Column(SAEnum(QuestionType), nullable=False, default=QuestionType.RATING)
    category        = Column(String(100), nullable=True)
    perspective     = Column(SAEnum(BSCPerspective), nullable=False, default=BSCPerspective.GENERAL)
    options         = Column(JSON, nullable=True)     # choices for MULTIPLE/LIKERT/RANKING
    scale_min       = Column(Integer, nullable=True, default=1)
    scale_max       = Column(Integer, nullable=True, default=5)
    is_required     = Column(Boolean, default=True, nullable=False)
    order_index     = Column(Integer, nullable=False, default=0)
    skip_logic      = Column(JSON, nullable=True)     # [{condition, jump_to_question_id}]

    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    survey         = relationship("Survey", back_populates="questions")
    bank_question  = relationship("SurveyQuestionBank", back_populates="survey_questions")

    __table_args__ = (
        Index("ix_sq_survey_id", "survey_id"),
        Index("ix_sq_order", "survey_id", "order_index"),
    )



class SurveyDistribution(Base):

    __tablename__ = "survey_distributions"

    id                  = Column(Integer, primary_key=True, index=True)
    survey_id           = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, unique=True)

    
    methods             = Column(JSON, nullable=False, default=list)  

    schedule_type       = Column(SAEnum(ScheduleType), nullable=False, default=ScheduleType.SEND_IMMEDIATELY)
    scheduled_at        = Column(DateTime, nullable=True)
    recurring_frequency = Column(SAEnum(RecurringFrequency), nullable=True)
    recurring_end_date  = Column(DateTime, nullable=True)
    event_trigger       = Column(String(255), nullable=True)  # e.g., "onboarding_complete"

    audience_type       = Column(SAEnum(TargetAudienceType), nullable=False, default=TargetAudienceType.ALL_EMPLOYEES)
    audience_filter     = Column(JSON, nullable=True)   
    total_recipients    = Column(Integer, nullable=True, default=0)

    shareable_link      = Column(Text, nullable=True)
    qr_code_data        = Column(Text, nullable=True)  

    emails_sent         = Column(Integer, nullable=True, default=0)
    emails_opened       = Column(Integer, nullable=True, default=0)
    surveys_started     = Column(Integer, nullable=True, default=0)
    surveys_completed   = Column(Integer, nullable=True, default=0)
    surveys_in_progress = Column(Integer, nullable=True, default=0)
    surveys_not_started = Column(Integer, nullable=True, default=0)
    reminders_sent      = Column(Integer, nullable=True, default=0)
    max_reminders       = Column(Integer, nullable=True, default=3)

    launched_at         = Column(DateTime, nullable=True)
    last_reminder_at    = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    survey = relationship("Survey", back_populates="distribution")

    __table_args__ = (
        Index("ix_sd_survey_id", "survey_id"),
    )


class SurveyResponse(Base):

    __tablename__ = "survey_responses"

    id              = Column(Integer, primary_key=True, index=True)
    survey_id       = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=True)  # null = anonymous

    answers         = Column(JSON, nullable=True, default=list)

    nps_score       = Column(Integer, nullable=True)
    overall_score   = Column(Float, nullable=True)

    is_anonymous    = Column(Boolean, default=False, nullable=False)
    is_complete     = Column(Boolean, default=False, nullable=False)
    started_at      = Column(DateTime, nullable=True)
    submitted_at    = Column(DateTime, nullable=True)
    ip_address      = Column(String(45), nullable=True)

    survey   = relationship("Survey", back_populates="responses")

    __table_args__ = (
        Index("ix_sr_survey_id", "survey_id"),
        Index("ix_sr_employee_id", "employee_id"),
        Index("ix_sr_submitted_at", "submitted_at"),
    )

class SurveyAnalytics(Base):

    __tablename__ = "survey_analytics"

    id                    = Column(Integer, primary_key=True, index=True)
    survey_id             = Column(Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, unique=True)


    total_recipients      = Column(Integer, nullable=True, default=0)
    total_responses       = Column(Integer, nullable=True, default=0)
    response_rate         = Column(Float, nullable=True, default=0.0)    
    completion_rate       = Column(Float, nullable=True, default=0.0)   
    average_nps_score     = Column(Float, nullable=True)
    avg_satisfaction      = Column(Float, nullable=True)

   
    department_comparison = Column(JSON, nullable=True, default=list)

    trend_data            = Column(JSON, nullable=True, default=list)

   
    sentiment_data        = Column(JSON, nullable=True, default=dict)

    
    question_results      = Column(JSON, nullable=True, default=list)

    refreshed_at          = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

  
    survey = relationship("Survey", back_populates="analytics")

    __table_args__ = (
        Index("ix_sa_survey_id", "survey_id"),
    )
