from sqlalchemy import (
    Column,
    Integer,
    String,
    Time,
    Boolean,
    DateTime
)

from sqlalchemy.sql import func

from core.database import Base


class Shift(Base):
    __tablename__ = "shifts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    shift_name = Column(
        String(100),
        nullable=False
    )

    shift_code = Column(
        String(50),
        unique=True,
        nullable=False
    )

    start_time = Column(
        Time,
        nullable=False
    )

    end_time = Column(
        Time,
        nullable=False
    )

    break_minutes = Column(
        Integer,
        default=60
    )

    grace_minutes = Column(
        Integer,
        default=15
    )

    weekly_off = Column(
        String(100)
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )