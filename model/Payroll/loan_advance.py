from sqlalchemy import (
    Column, Integer, String, Float, Date,
    DateTime, Text, ForeignKey, func
)
from sqlalchemy.orm import relationship

from core.database import Base


class LoanAdvance(Base):
    __tablename__ = "loan_advances"

    id                 = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loan_id            = Column(String(20), unique=True, nullable=False, index=True)  # LN001, LN002...

    # Employee
    employee_id        = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    employee           = relationship("Employee", back_populates="loan_advances",
                                      foreign_keys=[employee_id])

    # Loan details
    loan_type          = Column(String(100), nullable=False)
    # Educational loan | Emergency loan | Festival advance | Salary advance | Vehicle loan | Personal loan
    description        = Column(Text, nullable=True)
    interest_rate      = Column(Float, nullable=False, default=0.0)       # % per annum e.g. 6.5
    interest_method    = Column(String(50), nullable=True)                # Reducing Balance | No Interest | Flat
    repayment_method   = Column(String(100), nullable=False, default="Payroll Deduction")

    # Amount
    principal_amount   = Column(Float, nullable=False)
    amount_paid        = Column(Float, nullable=False, default=0.0)
    amount_pending     = Column(Float, nullable=False, default=0.0)

    # EMI & Tenure
    emi_amount         = Column(Float, nullable=True)
    tenure_months      = Column(Integer, nullable=True)

    # Dates
    issue_date         = Column(Date, nullable=False)
    start_date         = Column(Date, nullable=True)    # first EMI date
    end_date           = Column(Date, nullable=True)    # last EMI date
    next_due_date      = Column(Date, nullable=True)
    approved_date      = Column(Date, nullable=True)

    # Status: PENDING | ACTIVE | COMPLETED | REJECTED | CANCELLED
    status             = Column(String(50), nullable=False, default="PENDING", index=True)

    # Approval
    approved_by        = Column(String(255), nullable=True)
    remarks            = Column(Text, nullable=True)

    # Payroll linkage
    # payroll_id         = Column(Integer, ForeignKey("payrolls.id"), nullable=True)
    #payroll            = relationship("Payroll", back_populates="loan_advances")
    payroll_id         = Column(Integer, nullable=True)

    # Audit
    created_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at         = Column(DateTime(timezone=True), server_default=func.now(),
                                onupdate=func.now(), nullable=False)

    # EMI schedule rows
    emi_schedules      = relationship(
        "LoanEMISchedule",
        back_populates="loan",
        cascade="all, delete-orphan",
        order_by="LoanEMISchedule.installment_no",
    )


class LoanEMISchedule(Base):
    __tablename__ = "loan_emi_schedules"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    loan_id         = Column(Integer, ForeignKey("loan_advances.id"), nullable=False, index=True)
    loan            = relationship("LoanAdvance", back_populates="emi_schedules")

    installment_no  = Column(Integer, nullable=False)       # 1, 2, 3 ...
    due_date        = Column(Date, nullable=False)
    emi_amount      = Column(Float, nullable=False)
    principal_part  = Column(Float, nullable=True)
    interest_part   = Column(Float, nullable=True)
    paid_amount     = Column(Float, nullable=False, default=0.0)
    paid_date       = Column(Date, nullable=True)
    balance         = Column(Float, nullable=True)          # outstanding after this EMI

    # Status: PENDING | PAID | PARTIAL | OVERDUE
    status          = Column(String(50), nullable=False, default="PENDING")

    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now(), nullable=False)