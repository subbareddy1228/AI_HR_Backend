from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from core.database import Base
from datetime import datetime


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    survey_type = Column(String(100), nullable=False)  # Pulse Check/Exit Survey/Engagement/Custom
    questions = Column(JSON, nullable=True)  # array of question objects
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SurveyResponse(Base):
    __tablename__ = "survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("surveys.id"), nullable=False)
    employee_id = Column(Integer, nullable=True)
    responses = Column(JSON, nullable=True)  # [{question_id, answer}, ...]
    submitted_at = Column(DateTime, default=datetime.utcnow)
    is_anonymous = Column(Boolean, default=False)
