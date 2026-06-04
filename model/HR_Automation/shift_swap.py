# model/HR_Automation/shift_swap.py

from sqlalchemy import (
    Column,
    Integer,
    Date,
    String,
    ForeignKey
)

from core.database import Base


class ShiftSwapRequest(Base):

    __tablename__ = "shift_swap_requests"

    id = Column(Integer, primary_key=True)

    requester_employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    target_employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    swap_date = Column(Date)

    status = Column(
        String(20),
        default="PENDING"
    )