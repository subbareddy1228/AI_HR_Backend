# model/HR_Operations/buddy_program.py
# Buddy Program — Tab 4 of Promotions & Career Progression

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Numeric, Boolean
from core.database import Base
from datetime import datetime


class BuddyProgram(Base):
    __tablename__ = "buddy_programs"

    id                    = Column(Integer, primary_key=True, index=True)

    # The senior employee acting as buddy
    buddy_employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    buddy_code            = Column(String(20), nullable=True, unique=True)   # BUD001, BUD002 …

    status                = Column(String(20), nullable=False, default="Active")  # Active | Inactive

    # Performance
    rating                = Column(Numeric(3, 1), nullable=True)    # e.g. 4.7
    experience_years      = Column(Integer, nullable=True)           # yrs experience as buddy
    joined_as_buddy_date  = Column(Date, nullable=True)

    # Capacity
    max_capacity          = Column(Integer, default=3)
    current_assignments   = Column(Integer, default=0)
    feedback_count        = Column(Integer, default=0)

    remarks               = Column(Text, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BuddyAssignment(Base):
    __tablename__ = "buddy_assignments"

    id                       = Column(Integer, primary_key=True, index=True)
    buddy_id                 = Column(Integer, ForeignKey("buddy_programs.id"), nullable=False, index=True)
    new_joiner_employee_id   = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    assigned_date            = Column(Date, nullable=True)
    end_date                 = Column(Date, nullable=True)
    is_active                = Column(Boolean, default=True)

    feedback                 = Column(Text, nullable=True)
    feedback_date            = Column(Date, nullable=True)

    created_at               = Column(DateTime, default=datetime.utcnow)
    updated_at               = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
