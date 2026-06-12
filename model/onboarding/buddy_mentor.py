from sqlalchemy import (
    Column, Integer, String, Text, Date, Float,
    Boolean, ForeignKey, Enum as SAEnum, DateTime
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from core.database import Base




class ProgramType(str, enum.Enum):
    NEW_HIRE_BUDDY     = "New Hire Buddy Program"
    MENTORSHIP         = "Mentorship Program"
    CROSS_FUNCTIONAL   = "Cross Functional Buddy"


class ProgramStatus(str, enum.Enum):
    ACTIVE    = "Active"
    COMPLETED = "Completed"
    DRAFT     = "Draft"


class PairingStatus(str, enum.Enum):
    ACTIVE    = "Active"
    COMPLETED = "Completed"
    INACTIVE  = "Inactive"


class CommunicationType(str, enum.Enum):
    WEEKLY_CHECKIN     = "Weekly Checkin"
    MONTHLY_REVIEW     = "Monthly Review"
    AD_HOC             = "Ad Hoc"
    ONBOARDING_SESSION = "Onboarding Session"



class BuddyProgram(Base):
    __tablename__ = "buddy_programs"

    id           = Column(Integer, primary_key=True, index=True)
    program_name = Column(String(255), nullable=False)
    program_type = Column(SAEnum(ProgramType), nullable=False)
    description  = Column(Text, nullable=True)
    department   = Column(String(100), nullable=True, default="All")
    location     = Column(String(100), nullable=True, default="All")
    start_date   = Column(Date, nullable=False)
    end_date     = Column(Date, nullable=True)
    status       = Column(SAEnum(ProgramStatus), default=ProgramStatus.ACTIVE, nullable=False)
    created_by   = Column(String(100), nullable=False)
    created_on   = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    pairings         = relationship("BuddyPairing",      back_populates="program", cascade="all, delete-orphan")
    assignment_rules = relationship("AssignmentRule",     back_populates="program", cascade="all, delete-orphan")


class AssignmentRule(Base):
    __tablename__ = "buddy_assignment_rules"

    id           = Column(Integer, primary_key=True, index=True)
    program_id   = Column(Integer, ForeignKey("buddy_programs.id"), nullable=False)
    rule_text    = Column(String(500), nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    weight_score = Column(Integer, default=0, nullable=False)

    program = relationship("BuddyProgram", back_populates="assignment_rules")


class BuddyPairing(Base):
    __tablename__ = "buddy_pairings"

    id              = Column(Integer, primary_key=True, index=True)
    program_id      = Column(Integer, ForeignKey("buddy_programs.id"), nullable=False)
    
    buddy_id        = Column(Integer, ForeignKey("employees.id"), nullable=False)
    new_joiner_id   = Column(Integer, ForeignKey("employees.id"), nullable=False)
    match_score     = Column(Integer, nullable=True)         # 0-100
    assignment_date = Column(Date, nullable=False)
    last_checkin    = Column(Date, nullable=True)
    progress        = Column(Integer, default=0, nullable=False)   # percentage 0-100
    feedback_score  = Column(Float, nullable=True)                 # 0.0-5.0
    status          = Column(SAEnum(PairingStatus), default=PairingStatus.ACTIVE, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)

    program        = relationship("BuddyProgram", back_populates="pairings")
    feedbacks      = relationship("BuddyFeedback",      back_populates="pairing", cascade="all, delete-orphan")
    communications = relationship("BuddyCommunication", back_populates="pairing", cascade="all, delete-orphan")


class BuddyFeedback(Base):
    __tablename__ = "buddy_feedbacks"

    id                           = Column(Integer, primary_key=True, index=True)
    pairing_id                   = Column(Integer, ForeignKey("buddy_pairings.id"), nullable=False)
    submitted_by                 = Column(String(100), nullable=False)
    overall_rating               = Column(Integer, nullable=False)        # 1-5
    responsiveness               = Column(Integer, nullable=True)         # 1-5
    knowledge_sharing            = Column(Integer, nullable=True)         # 1-5
    support                      = Column(Integer, nullable=True)         # 1-5
    communication                = Column(Integer, nullable=True)         # 1-5
    overall_comments             = Column(Text, nullable=True)
    responsiveness_comments      = Column(Text, nullable=True)
    knowledge_sharing_comments   = Column(Text, nullable=True)
    support_comments             = Column(Text, nullable=True)
    communication_comments       = Column(Text, nullable=True)
    submitted_at                 = Column(DateTime, default=datetime.utcnow, nullable=False)

    pairing = relationship("BuddyPairing", back_populates="feedbacks")


class BuddyCommunication(Base):
    __tablename__ = "buddy_communications"

    id                  = Column(Integer, primary_key=True, index=True)
    pairing_id          = Column(Integer, ForeignKey("buddy_pairings.id"), nullable=False)
    communication_type  = Column(SAEnum(CommunicationType), nullable=False)
    date                = Column(Date, nullable=False)
    duration_minutes    = Column(Integer, nullable=True)
    next_checkin_date   = Column(Date, nullable=True)
    topics_discussed    = Column(Text, nullable=True)      # comma-separated
    follow_up_actions   = Column(Text, nullable=True)      # comma-separated
    additional_notes    = Column(Text, nullable=True)
    recorded_at         = Column(DateTime, default=datetime.utcnow, nullable=False)

    pairing = relationship("BuddyPairing", back_populates="communications")