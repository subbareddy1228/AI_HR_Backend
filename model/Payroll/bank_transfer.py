

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey
from core.database import Base
from datetime import datetime


class BankTransfer(Base):
    __tablename__ = "bank_transfers"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    employee_name = Column(String(255), nullable=False)
    bank_account = Column(String(100), nullable=False)
    bank_name = Column(String(255), nullable=False)
    ifsc_code = Column(String(20), nullable=False)
    transfer_amount = Column(Numeric(10, 2), nullable=False)
    transfer_date = Column(Date, nullable=False)
    utr_number = Column(String(100), nullable=True)
    status = Column(String(50), default="Pending")  # Pending/Initiated/Success/Failed
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
