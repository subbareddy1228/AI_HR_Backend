# FILE 5 of 18 | model/Payroll/loan_advance.py
# Model: LoanAdvance
# Table: loans_advances

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey
from core.database import Base
from datetime import datetime


class LoanAdvance(Base):
    __tablename__ = "loans_advances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    loan_type = Column(String(50), nullable=False)  # Loan/Salary Advance
    amount = Column(Numeric(10, 2), nullable=False)
    approved_amount = Column(Numeric(10, 2), nullable=True)
    emi_amount = Column(Numeric(10, 2), nullable=True)
    total_installments = Column(Integer, nullable=True)
    paid_installments = Column(Integer, default=0)
    start_date = Column(Date, nullable=True)
    status = Column(String(50), default="Pending")  # Pending/Approved/Rejected/Active/Closed
    reason = Column(Text, nullable=True)
    approved_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
