# model/HR_Operations/transfer.py
# Transfer & Movement Management — replaces the original stub
#
# Transfer Types visible in screenshots:
#   Internal Transfer | Location Transfer | Promotion Transfer | Department Transfer
#
# Statuses:
#   Pending | Approved | Rejected | Completed

from sqlalchemy import (
    Column, Integer, String, Date, Text,
    DateTime, ForeignKey, Boolean,
)
from core.database import Base
from datetime import datetime


class Transfer(Base):
    __tablename__ = "transfers"

    id               = Column(Integer, primary_key=True, index=True)

    # Auto-generated code: TRO01, TRO02 …
    transfer_code    = Column(String(20), nullable=True, unique=True)

    employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # From / To  ───────────────────────────────────────────────────────────────
    from_department  = Column(String(150), nullable=False)
    to_department    = Column(String(150), nullable=False)
    from_location    = Column(String(150), nullable=True)
    to_location      = Column(String(150), nullable=True)
    from_designation = Column(String(150), nullable=True)   # for Promotion Transfer
    to_designation   = Column(String(150), nullable=True)

    # Transfer type (matches badge colours in UI)
    # Internal Transfer | Location Transfer | Promotion Transfer | Department Transfer
    transfer_type    = Column(String(50), nullable=False)

    # Dates
    effective_date   = Column(Date, nullable=False)
    request_date     = Column(Date, nullable=True)

    # Status: Pending | Approved | Rejected | Completed
    status           = Column(String(30), nullable=False, default="Pending")

    # Approval
    approved_by      = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_date    = Column(Date, nullable=True)

    reason           = Column(Text, nullable=True)
    remarks          = Column(Text, nullable=True)

    # Flags updated when employee record is actually changed
    employee_record_updated = Column(Boolean, default=False)

    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
