# FILE 4 of 18 | model/Payroll/reimbursement.py
# Model: Reimbursement
# Table: reimbursements

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey
from core.database import Base
from datetime import datetime


class Reimbursement(Base):
    __tablename__ = "reimbursements"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    claim_type = Column(String(100), nullable=False)  # Travel/Medical/Food/Internet/Other
    amount = Column(Numeric(10, 2), nullable=False)
    claim_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    receipt_path = Column(String(500), nullable=True)
    status = Column(String(50), default="Pending")  # Pending/Approved/Rejected/Paid
    approved_by = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
