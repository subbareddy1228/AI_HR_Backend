# model/HR_Operations/promotion.py
# Promotions — Tab 3 of Promotions & Career Progression
# Replaces the original stub

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, Numeric, ForeignKey, Boolean
from core.database import Base
from datetime import datetime


class Promotion(Base):
    __tablename__ = "promotions"

    id                      = Column(Integer, primary_key=True, index=True)
    employee_id             = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Grade / designation change  (e.g. P3 → P4, Senior SE → Tech Lead)
    from_grade              = Column(String(50), nullable=True)
    to_grade                = Column(String(50), nullable=True)
    from_designation        = Column(String(150), nullable=False)
    to_designation          = Column(String(150), nullable=False)

    # Salary impact
    current_salary          = Column(Numeric(12, 2), nullable=True)
    revised_salary          = Column(Numeric(12, 2), nullable=True)
    salary_increase_percent = Column(Numeric(5, 2), nullable=True)   # auto-computed if omitted

    # Eligibility
    is_eligible             = Column(Boolean, default=True)
    tenure_years            = Column(Numeric(4, 1), nullable=True)   # e.g. 3.5

    # 5-step approval workflow  (M=Manager, D=Director, H=HR, P=Panel, L=Leadership)
    # Status: Under Review | Approved | Rejected | Pending
    status                  = Column(String(50), nullable=False, default="Under Review")
    approval_step           = Column(Integer, default=0)
    approval_total          = Column(Integer, default=5)
    step_m_done             = Column(Boolean, default=False)  # Manager
    step_d_done             = Column(Boolean, default=False)  # Director
    step_h_done             = Column(Boolean, default=False)  # HR
    step_p_done             = Column(Boolean, default=False)  # Panel
    step_l_done             = Column(Boolean, default=False)  # Leadership

    # Dates
    effective_date          = Column(Date, nullable=True)
    nomination_date         = Column(Date, nullable=True)
    review_date             = Column(Date, nullable=True)

    # Meta
    reason                  = Column(Text, nullable=True)
    letter_generated        = Column(Boolean, default=False)
    approved_by             = Column(Integer, ForeignKey("employees.id"), nullable=True)
    remarks                 = Column(Text, nullable=True)

    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
