from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone

from core.database import Base



# APP SESSION MODEL (FIXED)


class AppSession(Base):
    __tablename__ = "app_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # s OWNER
    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # APP INFO
    app_name = Column(String(255), index=True, nullable=False)
    category = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    path = Column(String(500), nullable=False)

    # METRICS
    cpu_usage = Column(Float, nullable=False)
    memory_usage = Column(Float, nullable=False)
    threads = Column(Integer, nullable=False)

    # TIME (timezone-safe)
    opened_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    closed_at = Column(DateTime(timezone=True), nullable=True)

    duration_seconds = Column(Integer, default=0)

    # RELATIONSHIP
    employee = relationship("Employee", back_populates="app_sessions")



# ACTIVITY MODEL (UNCHANGED)


class ProductivityActivity(Base):
    __tablename__ = "productivity_activities"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    team_id = Column(
        Integer,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    activity_type = Column(String(255), nullable=False, index=True)
    description = Column(String(255), nullable=True)
    activity_metadata = Column(Text, nullable=True)

    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    productive = Column(String(50), nullable=True)

    employee = relationship("Employee", back_populates="activities")
    department = relationship("Department", back_populates="activities")
    team = relationship("Team", back_populates="activities")

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
