# model/HR_Automation/shift_roster.py

from sqlalchemy import (
    Column,
    Integer,
    Date,
    ForeignKey
)

from core.database import Base


class ShiftRoster(Base):

    __tablename__ = "shift_rosters"

    id = Column(Integer, primary_key=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id")
    )

    shift_id = Column(
        Integer,
        ForeignKey("shifts.id")
    )

    roster_date = Column(
        Date,
        nullable=False
    )