"""
model/HR_Operations/notice_period.py

Notice Period Tracking & Management
------------------------------------
Tables:

1. NoticePeriod          -> core record per resignation (Daily Countdown Tracker)
2. ResignationSubmission -> "Submit Resignation" modal payload + AI prediction
3. BuyoutRequest         -> "Buyout Requests" tab
4. WaiverRequest         -> "Waiver Requests" tab
5. WaiverDocument        -> documents attached to a waiver request ("3 docs")
6. CounterOffer          -> "Counter Offers & Retention" tab (AI retention %)
7. ExtensionRequest      -> "Extension Requests" tab
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    DateTime,
    ForeignKey,
    Numeric,
    Float,
)
from core.database import Base
from datetime import datetime


# ======================================================
# 1. NOTICE PERIOD (core record / Daily Countdown Tracker)
# ======================================================
class NoticePeriod(Base):
    __tablename__ = "notice_periods"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    notice_start_date = Column(Date, nullable=False)
    notice_end_date = Column(Date, nullable=False)
    notice_period_days = Column(Integer, nullable=False)    # contractual notice days
    serving_days = Column(Integer, nullable=True)            # actual days served

    waiver_requested = Column(String(10), nullable=False, server_default="NO")   # YES | NO
    waiver_approved = Column(String(10), nullable=False, server_default="NO")    # YES | NO
    buyout_amount = Column(Integer, nullable=True)           # if notice is bought out

    # SERVING | COMPLETED | WAIVED | BUYOUT | COUNTER_OFFER_PENDING
    status = Column(String(50), nullable=False, server_default="SERVING")

    manager_ack_status = Column(String(50), nullable=False, server_default="PENDING")  # PENDING | ACKNOWLEDGED

    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 2. RESIGNATION SUBMISSION (the "Submit Resignation" modal)
# ======================================================
class ResignationSubmission(Base):
    __tablename__ = "resignation_submissions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id"), nullable=True, index=True)

    department = Column(String(150), nullable=False)
    role = Column(String(150), nullable=False)

    resignation_date = Column(Date, nullable=False)
    notice_period_days = Column(Integer, nullable=False)     # 30/45/60/90 days

    resignation_reason = Column(String(150), nullable=False)  # Better opportunity | Higher studies | Personal | Relocation | Other
    additional_comments = Column(Text, nullable=True)

    reporting_manager_email = Column(String(255), nullable=False)

    # AI prediction fields -> powers "95% Prediction Accuracy" / Retention Success
    ai_retention_probability = Column(Float, nullable=True)   # 0-100
    ai_risk_level = Column(String(20), nullable=True)         # LOW | MEDIUM | HIGH
    ai_recommendation = Column(Text, nullable=True)

    status = Column(String(50), nullable=False, server_default="SUBMITTED")  # SUBMITTED | ACKNOWLEDGED | WITHDRAWN

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 3. BUYOUT REQUEST
# ======================================================
class BuyoutRequest(Base):
    __tablename__ = "buyout_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id"), nullable=True, index=True)

    requested_date = Column(Date, nullable=False)
    monthly_salary = Column(Numeric(12, 2), nullable=False)
    days_to_buyout = Column(Integer, nullable=False)
    buyout_amount = Column(Numeric(12, 2), nullable=False)   # (monthly_salary / 30) * days_to_buyout

    # PENDING | APPROVED | REJECTED
    status = Column(String(50), nullable=False, server_default="PENDING")

    # Multi-level approval, mirrors the M / HR / F chips in the screenshot
    manager_approval = Column(String(20), nullable=False, server_default="PENDING")  # PENDING | APPROVED | REJECTED
    hr_approval = Column(String(20), nullable=False, server_default="PENDING")
    finance_approval = Column(String(20), nullable=False, server_default="PENDING")

    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 4. WAIVER REQUEST
# ======================================================
class WaiverRequest(Base):
    __tablename__ = "waiver_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id"), nullable=True, index=True)

    requested_date = Column(Date, nullable=False)
    waiver_days = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)

    # PENDING | APPROVED | REJECTED
    status = Column(String(50), nullable=False, server_default="PENDING")

    manager_approval = Column(String(20), nullable=False, server_default="PENDING")
    hr_approval = Column(String(20), nullable=False, server_default="PENDING")
    director_approval = Column(String(20), nullable=False, server_default="PENDING")

    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 5. WAIVER DOCUMENT  -> the "3 docs" / "2 docs" badge
# ======================================================
class WaiverDocument(Base):
    __tablename__ = "waiver_documents"

    id = Column(Integer, primary_key=True, index=True)
    waiver_request_id = Column(Integer, ForeignKey("waiver_requests.id"), nullable=False, index=True)

    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=True)

    uploaded_at = Column(DateTime, default=datetime.utcnow)


# ======================================================
# 6. COUNTER OFFER & RETENTION
# ======================================================
class CounterOffer(Base):
    __tablename__ = "counter_offers"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id"), nullable=True, index=True)

    current_salary = Column(Numeric(12, 2), nullable=False)
    offered_salary = Column(Numeric(12, 2), nullable=False)
    hike_percent = Column(Float, nullable=False)             # (offered - current) / current * 100

    # AI-predicted likelihood the employee stays if offer is accepted, 0-100
    retention_probability = Column(Float, nullable=True)
    ai_rationale = Column(Text, nullable=True)

    # PENDING | ACCEPTED | REJECTED
    status = Column(String(50), nullable=False, server_default="PENDING")

    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 7. EXTENSION REQUEST
# ======================================================
class ExtensionRequest(Base):
    __tablename__ = "extension_requests"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notice_period_id = Column(Integer, ForeignKey("notice_periods.id"), nullable=True, index=True)

    current_lwd = Column(Date, nullable=False)               # current last working day
    requested_lwd = Column(Date, nullable=False)              # requested new last working day
    extension_days = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)

    # PENDING | APPROVED | REJECTED
    status = Column(String(50), nullable=False, server_default="PENDING")

    manager_approval = Column(String(20), nullable=False, server_default="PENDING")
    hr_approval = Column(String(20), nullable=False, server_default="PENDING")

    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)