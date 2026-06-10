

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey
from core.database import Base
from datetime import datetime


class FinalSettlement(Base):
    __tablename__ = "final_settlements"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    last_working_date = Column(Date, nullable=False)
    notice_period_days = Column(Integer, default=0)
    notice_period_shortfall_days = Column(Integer, default=0)
    basic_salary = Column(Numeric(10, 2), nullable=False)
    gratuity_amount = Column(Numeric(10, 2), default=0)
    leave_encashment_days = Column(Integer, default=0)
    leave_encashment_amount = Column(Numeric(10, 2), default=0)
    pending_reimbursements = Column(Numeric(10, 2), default=0)
    loan_recovery = Column(Numeric(10, 2), default=0)
    tds_deduction = Column(Numeric(10, 2), default=0)
    total_payable = Column(Numeric(10, 2), nullable=False)
    settlement_status = Column(String(50), default="Draft")  # Draft/Pending Approval/Approved/Paid
    approved_by = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
