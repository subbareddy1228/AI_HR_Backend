

from datetime import datetime
from sqlalchemy import (
    Column, Integer, Boolean, DateTime,
    ForeignKey, UniqueConstraint,
)
from core.database import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id                      = Column(Integer, primary_key=True, index=True)
    tenant_id               = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

   
    email_system_alerts     = Column(Boolean, default=True,  nullable=False)
    email_payroll_updates   = Column(Boolean, default=True,  nullable=False)
    email_leave_approvals   = Column(Boolean, default=True,  nullable=False)
    email_attendance_reminders = Column(Boolean, default=True,  nullable=False)
    email_policy_updates    = Column(Boolean, default=True,  nullable=False)
    email_security_alerts   = Column(Boolean, default=True,  nullable=False)
    email_weekly_reports    = Column(Boolean, default=False, nullable=False)
    email_monthly_summaries = Column(Boolean, default=True,  nullable=False)

   
    push_mobile_alerts      = Column(Boolean, default=True,  nullable=False)
    push_desktop_alerts     = Column(Boolean, default=False, nullable=False)
    push_instant_updates    = Column(Boolean, default=True,  nullable=False)
    push_scheduled_summary  = Column(Boolean, default=False, nullable=False)

    
    sms_urgent_alerts       = Column(Boolean, default=True,  nullable=False)
    sms_otp_verification    = Column(Boolean, default=True,  nullable=False)
    sms_payroll_credits     = Column(Boolean, default=False, nullable=False)
    sms_attendance_reminders = Column(Boolean, default=False, nullable=False)

   
    created_at              = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at              = Column(DateTime, default=datetime.utcnow,
                                     onupdate=datetime.utcnow, nullable=False)
    updated_by              = Column(Integer, ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_notification_prefs_tenant"),
    )
