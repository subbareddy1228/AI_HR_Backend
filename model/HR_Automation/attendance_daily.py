from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    ForeignKey
)

from sqlalchemy.sql import func

from core.database import Base


class AttendanceDaily(Base):
    __tablename__ = "attendance_daily"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False,
        index=True
    )

    attendance_date = Column(
        Date,
        nullable=False,
        index=True
    )

    first_in = Column(
        DateTime,
        nullable=True
    )

    last_out = Column(
        DateTime,
        nullable=True
    )

    work_minutes = Column(
        Integer,
        default=0
    )

    break_minutes = Column(
        Integer,
        default=0
    )

    overtime_minutes = Column(
        Integer,
        default=0
    )

    late_minutes = Column(
        Integer,
        default=0
    )

    attendance_status = Column(
        String(20),
        default="P"
    )

    remarks = Column(
        String(500),
        nullable=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )