
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from core.database import Base
import enum


class ApprovalStatus(str, enum.Enum):
    PENDING   = "Pending"
    APPROVED  = "Approved"
    REJECTED  = "Rejected"
    ESCALATED = "Escalated"
    WITHDRAWN = "Withdrawn"
    ON_HOLD   = "On Hold"


class ApprovalPriority(str, enum.Enum):
    LOW    = "Low"
    MEDIUM = "Medium"
    HIGH   = "High"
    URGENT = "Urgent"


class ApprovalSLAStatus(str, enum.Enum):
    ON_TRACK = "On Track"
    AT_RISK  = "At Risk"
    BREACHED = "SLA Breached"
    RESOLVED = "Resolved"


class ApprovalViewMode(str, enum.Enum):
    EMPLOYEE = "Employee"
    MANAGER  = "Manager"


class ApprovalsDashboard(Base):


    __tablename__ = "approvals_dashboard"


    id               = Column(BigInteger, primary_key=True, index=True, autoincrement=True)


    approval_code    = Column(String(30), unique=True, nullable=False, index=True)


    request_mgmt_id  = Column(
        BigInteger,
        ForeignKey("request_management.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    reference_type   = Column(String(100), nullable=False, index=True)

    period_start     = Column(String(20), nullable=True)   
    period_end       = Column(String(20), nullable=True)   
 
    tags             = Column(String(500), nullable=True)

    employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    employee_name    = Column(String(255), nullable=True)
    employee_email   = Column(String(255), nullable=True)
    employee_code    = Column(String(50),  nullable=True)   
    department       = Column(String(100), nullable=True)
    designation      = Column(String(100), nullable=True)
    location         = Column(String(100), nullable=True)


    subject          = Column(String(500), nullable=False)
    description      = Column(Text, nullable=True)

    assigned_to      = Column(String(255), nullable=True, index=True)
    assigned_to_id   = Column(Integer, ForeignKey("employees.id"), nullable=True)
    assigned_at      = Column(DateTime, nullable=True)

  
    actioned_by      = Column(String(255), nullable=True)
    actioned_by_id   = Column(Integer, ForeignKey("employees.id"), nullable=True)
    action_comments  = Column(Text, nullable=True)
    actioned_at      = Column(DateTime, nullable=True)

 
    status           = Column(
        String(50),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    priority         = Column(String(20), nullable=False, default=ApprovalPriority.MEDIUM)

    sla_due_date     = Column(DateTime, nullable=True)
    sla_days_allowed = Column(Integer,  nullable=True)   # numeric SLA, e.g. 3 days
    sla_status       = Column(
        String(30),
        nullable=False,
        default=ApprovalSLAStatus.ON_TRACK,
        index=True,
    )

    is_escalated          = Column(Boolean, default=False, nullable=False)
    escalated_to          = Column(String(255), nullable=True)
    escalated_to_id       = Column(Integer, ForeignKey("employees.id"), nullable=True)
    escalated_at          = Column(DateTime, nullable=True)
    escalation_reason     = Column(Text, nullable=True)
    auto_escalated        = Column(Boolean, default=False, nullable=False)

    workflow_instance_id  = Column(
        Integer,
        ForeignKey("workflow_engine_instances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_deleted       = Column(Boolean, default=False, nullable=False)
    deleted_at       = Column(DateTime, nullable=True)
    deleted_by       = Column(String(255), nullable=True)
    submitted_at     = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

   
    history     = relationship(
        "ApprovalHistory",
        back_populates="approval",
        cascade="all, delete-orphan",
        order_by="ApprovalHistory.changed_at",
    )
    comments    = relationship(
        "ApprovalDashboardComment",
        back_populates="approval",
        cascade="all, delete-orphan",
        order_by="ApprovalDashboardComment.created_at",
    )

    __table_args__ = (
        Index("ix_apd_status_priority",   "status", "priority"),
        Index("ix_apd_assigned_status",   "assigned_to_id", "status"),
        Index("ix_apd_employee_status",   "employee_id", "status"),
        Index("ix_apd_sla_status",        "sla_status"),
        Index("ix_apd_submitted_at",      "submitted_at"),
        Index("ix_apd_ref_type_status",   "reference_type", "status"),
    )



class ApprovalHistory(Base):

    __tablename__ = "approval_history"

    id           = Column(Integer,   primary_key=True, index=True, autoincrement=True)
    approval_id  = Column(
        BigInteger,
        ForeignKey("approvals_dashboard.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_status  = Column(String(50), nullable=True)
    to_status    = Column(String(50), nullable=False)
    changed_by   = Column(String(255), nullable=True)
    changed_by_id= Column(Integer, ForeignKey("employees.id"), nullable=True)
    note         = Column(Text, nullable=True)
    changed_at   = Column(DateTime, default=datetime.utcnow, nullable=False)

    approval = relationship("ApprovalsDashboard", back_populates="history")

    __table_args__ = (
        Index("ix_aph_approval_changed_at", "approval_id", "changed_at"),
    )


class ApprovalDashboardComment(Base):

    __tablename__ = "approval_dashboard_comments"

    id           = Column(Integer,   primary_key=True, index=True, autoincrement=True)
    approval_id  = Column(
        BigInteger,
        ForeignKey("approvals_dashboard.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id    = Column(Integer, ForeignKey("employees.id"), nullable=True)
    author_name  = Column(String(255), nullable=True)
    body         = Column(Text, nullable=False)
    is_internal  = Column(Boolean, default=False, nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    approval = relationship("ApprovalsDashboard", back_populates="comments")

    __table_args__ = (
        Index("ix_adc_approval_created", "approval_id", "created_at"),
    )



class ApprovalDelegation(Base):

    __tablename__ = "approval_delegations"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    delegator_id    = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    delegator_name  = Column(String(255), nullable=True)
    delegate_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    delegate_name   = Column(String(255), nullable=True)
    valid_from      = Column(DateTime, nullable=False)
    valid_until     = Column(DateTime, nullable=False)
    is_active       = Column(Boolean, default=True, nullable=False)
    reason          = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_adl_delegator_active",  "delegator_id", "is_active"),
        Index("ix_adl_delegate_active",   "delegate_id",  "is_active"),
        Index("ix_adl_validity",          "valid_from", "valid_until"),
    )
