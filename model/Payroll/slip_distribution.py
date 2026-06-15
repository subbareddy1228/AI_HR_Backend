# model/Payroll/slip_distribution.py
# Models: SlipDistributionLog, SlipSettings
# Tables: slip_distribution_logs, slip_settings

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from core.database import Base
from datetime import datetime


class SlipDistributionLog(Base):
    __tablename__ = "slip_distribution_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    salary_slip_id      = Column(Integer, ForeignKey("salary_slips.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False)
    distribution_method = Column(String(20), nullable=False)   # 'email' | 'download' | 'portal'
    recipient_email     = Column(String(255), nullable=True)
    sent_at             = Column(DateTime, default=datetime.utcnow)
    sent_by             = Column(String(255), nullable=True)   # HR user email
    status              = Column(String(20), default="sent")   # 'sent' | 'failed' | 'bounced'
    error_message       = Column(Text, nullable=True)


class SlipSettings(Base):
    __tablename__ = "slip_settings"

    id                      = Column(Integer, primary_key=True, index=True)
    company_name            = Column(String(255), nullable=True)
    company_address         = Column(Text, nullable=True)
    signatory_name          = Column(String(255), nullable=True)
    footer_text             = Column(Text, nullable=True)
    confidentiality_note    = Column(Text, nullable=True)
    email_subject_template  = Column(String(500), nullable=True,
                                     default="Your Salary Slip for [Month Year]")
    email_body_template     = Column(Text, nullable=True,
                                     default=(
                                         "Dear [Employee Name],\n\n"
                                         "Please find attached your salary slip for [Month Year].\n\n"
                                         "Net Pay: [Net Pay]\n\n"
                                         "Password: [Password]\n\n"
                                         "Regards,\nHR Department"
                                     ))
    password_protect        = Column(Boolean, default=True)
    password_type           = Column(String(20), default="dob")   # 'dob' | 'employee_id' | 'custom'
    custom_password         = Column(String(100), nullable=True)
    auto_email_on_publish   = Column(Boolean, default=False)
    retention_months        = Column(Integer, default=12)
    allow_revisions         = Column(Boolean, default=True)
    revision_window_days    = Column(Integer, default=7)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
