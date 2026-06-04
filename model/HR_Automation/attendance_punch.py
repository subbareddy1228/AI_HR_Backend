from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    Text,
    ForeignKey
)

from sqlalchemy.sql import func

from core.database import Base


class AttendancePunch(Base):
    __tablename__ = "attendance_punches"

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

    punch_time = Column(
        DateTime,
        nullable=False
    )

    punch_type = Column(
        String(30),
        nullable=False
    )
    # CHECKIN
    # BREAK_START
    # BREAK_END
    # CHECKOUT

    attendance_mode = Column(
        String(30),
        nullable=False
    )
    # SELFIE
    # GPS
    # WEB
    # REMOTE
    # BIOMETRIC

    latitude = Column(
        Float,
        nullable=True
    )

    longitude = Column(
        Float,
        nullable=True
    )

    location = Column(
        String(255),
        nullable=True
    )

    selfie_url = Column(
        Text,
        nullable=True
    )

    verified = Column(
        Boolean,
        default=False
    )

    remarks = Column(
        Text,
        nullable=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )