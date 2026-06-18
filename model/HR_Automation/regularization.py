import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
)

from core.database import Base


class RegularizationStatus(str, enum.Enum):
    pending = "Pending"
    approved = "Approved"
    rejected = "Rejected"


class RegularizationRequest(Base):
    

    __tablename__ = "regularization_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    request_type = Column(String(100), nullable=False, index=True)
    

    request_date = Column(Date, nullable=False)  # the attendance date being corrected

    original_check_in = Column(String(20), nullable=True)
    original_check_out = Column(String(20), nullable=True)
    requested_check_in = Column(String(20), nullable=True)
    requested_check_out = Column(String(20), nullable=True)

    reason = Column(Text, nullable=False)

    status = Column(
        SAEnum(RegularizationStatus, values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        default=RegularizationStatus.pending,
        nullable=False,
        index=True,
    )

    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by = Column(Integer, ForeignKey("user.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_comments = Column(Text, nullable=True)

    is_bulk = Column(Boolean, default=False)
    bulk_batch_id = Column(String(64), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegularizationAutoRejectRule(Base):
    

    __tablename__ = "regularization_auto_reject_rules"

    id = Column(Integer, primary_key=True, index=True)
    request_type = Column(String(100), nullable=False, unique=True)
    days_threshold = Column(Integer, nullable=False, default=7)
    is_enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)