from sqlalchemy import (
    Column,
    Integer,
    Date,
    ForeignKey
)

from core.database import Base


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    id = Column(
        Integer,
        primary_key=True
    )

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False
    )

    shift_id = Column(
        Integer,
        ForeignKey("shifts.id"),
        nullable=False
    )

    effective_from = Column(
        Date,
        nullable=False
    )

    effective_to = Column(
        Date,
        nullable=True
    )