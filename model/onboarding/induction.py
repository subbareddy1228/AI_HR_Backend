from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime,
    Boolean, Float, ForeignKey, Enum as SAEnum
)
from core.database import Base


class InductionProgram(Base):
    __tablename__ = "induction_programs"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(255), nullable=False)           # "Q1 2024 New Hire Orientation"
    description = Column(Text, nullable=True)                   # sub-title under name
    type        = Column(String(50),  nullable=False, default="batch")     # batch | individual
    status      = Column(String(50),  nullable=False, default="Upcoming")  # Upcoming | Ongoing | Completed

    
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)

    
    max_participants = Column(Integer, nullable=True)

    
    avg_rating  = Column(Float, default=0.0)

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InductionParticipant(Base):
    
    __tablename__ = "induction_participants"

    id          = Column(Integer, primary_key=True, index=True)
    program_id  = Column(Integer, ForeignKey("induction_programs.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id",           ondelete="CASCADE"), nullable=False)

    
    attendance  = Column(String(20), nullable=False, default="Not Marked")

    
    rating      = Column(Float, nullable=True)

    enrolled_at = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InductionSession(Base):
    
    __tablename__ = "induction_sessions"

    id          = Column(Integer, primary_key=True, index=True)
    program_id  = Column(Integer, ForeignKey("induction_programs.id", ondelete="CASCADE"), nullable=False)

    title       = Column(String(255), nullable=False)   # "Introduction to company culture, values,..."
    description = Column(Text, nullable=True)

    session_date = Column(Date, nullable=False)
    start_time   = Column(String(10), nullable=False)   # "9:00 AM"
    end_time     = Column(String(10), nullable=False)   # "10:30 AM"
    duration_hrs = Column(Float, nullable=True)         # 1.5 hrs

    mode         = Column(String(50), nullable=False, default="on-site")  # on-site | virtual | hybrid
    status       = Column(String(50), nullable=False, default="Upcoming") # Upcoming | Ongoing | Completed

    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InductionPolicy(Base):
   
    __tablename__ = "induction_policies"

    id             = Column(Integer, primary_key=True, index=True)
    title          = Column(String(255), nullable=False)   # "Employee Code of Conduct"
    category       = Column(String(100), nullable=False)   # general | compliance | security
    version        = Column(String(20),  nullable=False)   # "Version 3.2"
    effective_date = Column(Date,        nullable=False)
    status         = Column(String(50),  nullable=False, default="Draft")  # Draft | Published | Mandatory

    total_employees    = Column(Integer, default=0)   # denominator in "145/150"
    completed_employees = Column(Integer, default=0)  # numerator

    total_modules      = Column(Integer, default=0)   # "0/3 modules"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PolicyAcknowledgment(Base):
    
    __tablename__ = "policy_acknowledgments"

    id          = Column(Integer, primary_key=True, index=True)
    policy_id   = Column(Integer, ForeignKey("induction_policies.id", ondelete="CASCADE"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id",          ondelete="CASCADE"), nullable=False)

    acknowledged    = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime, nullable=True)

    
    modules_completed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)