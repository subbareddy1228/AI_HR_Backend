# FILE 4 of 18 | model/Payroll/reimbursement.py
# Model: Reimbursement
# Table: reimbursements

# from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Text, ForeignKey
# from core.database import Base
# from datetime import datetime


# class Reimbursement(Base):
#     __tablename__ = "reimbursements"

#     id = Column(Integer, primary_key=True, index=True)
#     employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
#     claim_type = Column(String(100), nullable=False)  # Travel/Medical/Food/Internet/Other
#     amount = Column(Numeric(10, 2), nullable=False)
#     claim_date = Column(Date, nullable=False)
#     description = Column(Text, nullable=True)
#     receipt_path = Column(String(500), nullable=True)
#     status = Column(String(50), default="Pending")  # Pending/Approved/Rejected/Paid
#     approved_by = Column(String(255), nullable=True)
#     remarks = Column(Text, nullable=True)
#     created_at = Column(DateTime, default=datetime.utcnow)


#model/Payroll/reimbursement.py
# Model: Reimbursement
# Table: reimbursements

from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship

from core.database import Base


class Reimbursement(Base):
    __tablename__ = "reimbursements"

    id             = Column(Integer, primary_key=True, index=True, autoincrement=True)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Claim details
    claim_type     = Column(String(100), nullable=False)          # Travel, Meals, Medical, etc.
    description    = Column(Text, nullable=True)
    amount         = Column(Float, nullable=False)
    currency       = Column(String(10), nullable=False, default="INR")
    expense_date   = Column(Date, nullable=False)

    # Receipt
    receipt_url      = Column(String(500), nullable=True)
    receipt_filename = Column(String(255), nullable=True)

    # Status:  PENDING | APPROVED | REJECTED
    status         = Column(String(50), nullable=False, default="PENDING")

    # Approval info
    approved_by    = Column(String(255), nullable=True)
    remarks        = Column(Text, nullable=True)

    # Payment info
    payment_mode      = Column(String(100), nullable=True)   # Bank Transfer, Cash, Cheque
    payment_reference = Column(String(100), nullable=True)
    paid_at           = Column(DateTime(timezone=True), nullable=True)

    # Payroll linkage
    payroll_id     = Column(Integer, ForeignKey("payrolls.id"), nullable=True)

    # Audit
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at     = Column(DateTime(timezone=True), server_default=func.now(),
                            onupdate=func.now(), nullable=False)

    # Relationships
    employee       = relationship("Employee", back_populates="reimbursements",
                                  foreign_keys=[employee_id])
    payroll        = relationship("Payroll", back_populates="reimbursements")