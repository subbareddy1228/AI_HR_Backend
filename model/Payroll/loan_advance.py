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


# model/Payroll/loan_advance.py
# Model: LoanAdvance
# Table: loans_advances, loan_emi_schedules

from sqlalchemy import (
    Column, Integer, String, Float, Date,
    DateTime, Text, ForeignKey, func
)
from sqlalchemy.orm import relationship

from core.database import Base


class LoanAdvance(Base):
    __tablename__ = "loan_advances"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loan_id     = Column(String(50), unique=True, nullable=False, index=True)  # e.g. LN001

    # Employee
    employee_id  = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee     = relationship("Employee", back_populates="loan_advances",
                                foreign_keys=[employee_id])

    # Loan details
    loan_type         = Column(String(100), nullable=False)   # Educational, Emergency, Vehicle, Salary Advance, Personal
    description       = Column(Text, nullable=True)

    # Amount
    principal_amount  = Column(Float, nullable=False)         # Total loan amount
    amount_paid       = Column(Float, nullable=False, default=0.0)
    amount_pending    = Column(Float, nullable=False, default=0.0)  # principal - paid

    # Interest
    interest_method   = Column(String(50), nullable=True)     # Reducing Balance / No Interest / Flat
    interest_rate     = Column(Float, nullable=True, default=0.0)   # % per annum

    # EMI & repayment
    emi_amount        = Column(Float, nullable=True)           # monthly EMI
    tenure_months     = Column(Integer, nullable=True)         # total months
    repayment_method  = Column(String(100), nullable=True, default="Payroll Deduction")

    # Dates
    issue_date        = Column(Date, nullable=False)
    start_date        = Column(Date, nullable=True)            # first EMI date
    end_date          = Column(Date, nullable=True)            # last EMI date
    next_due_date     = Column(Date, nullable=True)

    # Status: PENDING | ACTIVE | COMPLETED | REJECTED | CANCELLED
    status            = Column(String(50), nullable=False, default="PENDING")

    # Approval
    approved_by       = Column(String(255), nullable=True)
    remarks           = Column(Text, nullable=True)

    # Payroll linkage
    payroll_id        = Column(Integer, ForeignKey("payrolls.id"), nullable=True)
    payroll           = relationship("Payroll", back_populates="loan_advances")

    # Audit
    created_at        = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at        = Column(DateTime(timezone=True), server_default=func.now(),
                               onupdate=func.now(), nullable=False)

    # EMI schedule
    emi_schedules     = relationship(
        "LoanEMISchedule",
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="LoanEMISchedule.due_date"
    )


class LoanEMISchedule(Base):
    __tablename__ = "loan_emi_schedules"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loan_id         = Column(Integer, ForeignKey("loan_advances.id"), nullable=False, index=True)
    loan            = relationship("LoanAdvance", back_populates="emi_schedules")

    installment_no  = Column(Integer, nullable=False)          # 1, 2, 3 ...
    due_date        = Column(Date, nullable=False)
    emi_amount      = Column(Float, nullable=False)
    principal_part  = Column(Float, nullable=True)
    interest_part   = Column(Float, nullable=True)
    paid_amount     = Column(Float, nullable=False, default=0.0)
    paid_date       = Column(Date, nullable=True)
    balance         = Column(Float, nullable=True)             # outstanding after this EMI

    # Status: PENDING | PAID | OVERDUE | PARTIAL
    status          = Column(String(50), nullable=False, default="PENDING")

    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now(), nullable=False)