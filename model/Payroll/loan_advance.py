"""
LoanAdvance Model — Payroll Management → Advances & Loan Management

UI elements covered:
  • Filter tabs        — All Loans / Pending / Active / Completed (derived from `status`)
  • KPI cards          — Total Loans, Active Loans, Total Amount, Pending Amount
  • Search & filters   — by employee name/ID/loan ID, loan type, status
  • Table columns      — Employee Details, Designation, Department, Loan Type
                          (+ interest %, deduction mode), Status (+ approval sub-badge),
                          Issue Date (+ end date), Interest Method (+ rate),
                          Amount Details (+ paid/pending), EMI & Tenure (+ next due),
                          Actions (view/edit/approve/reject/delete)
  • Apply for Loan modal — create request

Status lifecycle:  PENDING → APPROVED → ACTIVE → COMPLETED
                              └──────→ REJECTED
                   ACTIVE   → DEFAULTED (optional, for overdue EMIs)
"""

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text, func,
)
from sqlalchemy.orm import relationship

from core.database import Base


class LoanAdvance(Base):
    __tablename__ = "loans_advances"

    id = Column(Integer, primary_key=True, index=True)
    loan_code = Column(String(20), unique=True, nullable=False, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee_code  = Column(String(50),  nullable=False)
    employee_name  = Column(String(255), nullable=False)
    designation    = Column(String(150), nullable=True)
    department     = Column(String(150), nullable=True)
    loan_type = Column(String(50), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(Text, nullable=True)
    interest_rate   = Column(Numeric(5, 2), nullable=False, server_default="0")
    interest_method = Column(String(50), nullable=False, server_default="Interest Free")
    repayment_mode = Column(String(50), nullable=False, server_default="Payroll Deduction")
    status        = Column(String(20), nullable=False, server_default="PENDING", index=True)
    approved_amount = Column(Numeric(12, 2), nullable=True)
    approved_by     = Column(String(255), nullable=True)
    approved_at     = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    emi_amount          = Column(Numeric(12, 2), nullable=True)
    total_installments   = Column(Integer, nullable=True)   
    paid_installments    = Column(Integer, nullable=False, server_default="0")
    issue_date  = Column(Date, nullable=True) 
    end_date    = Column(Date, nullable=True) 
    next_due_date = Column(Date, nullable=True)
    closed_date = Column(Date, nullable=True)  
    total_paid    = Column(Numeric(12, 2), nullable=False, server_default="0")
    total_pending = Column(Numeric(12, 2), nullable=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(),
                        onupdate=func.now())

    repayments = relationship(
        "LoanRepayment",
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="LoanRepayment.installment_number",
    )


class LoanRepayment(Base):

    __tablename__ = "loan_repayments"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans_advances.id", ondelete="CASCADE"),
                     nullable=False, index=True)

    installment_number = Column(Integer, nullable=False)
    due_date            = Column(Date, nullable=False, index=True)
    emi_amount           = Column(Numeric(12, 2), nullable=False)
    status      = Column(String(20), nullable=False, server_default="PENDING")
    paid_amount = Column(Numeric(12, 2), nullable=True)
    paid_date   = Column(Date, nullable=True)
    payment_reference = Column(String(150), nullable=True)  # payroll run ref / transaction id

    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(),
                        onupdate=func.now())

    loan = relationship("LoanAdvance", back_populates="repayments")
