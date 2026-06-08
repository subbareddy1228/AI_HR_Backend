from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from core.database import Base


class Objective(Base):
    __tablename__ = "objectives"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id = Column(Integer, nullable=True, index=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default="Not Started", nullable=False)
    progress = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    key_results = relationship("KeyResult", back_populates="objective", cascade="all, delete-orphan")


class KeyResult(Base):
    __tablename__ = "key_results"

    id = Column(Integer, primary_key=True, index=True)
    objective_id = Column(Integer, ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    target_value = Column(Float, nullable=False, default=100.0)
    current_value = Column(Float, nullable=False, default=0.0)
    unit = Column(String(50), nullable=True)
    progress = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="Not Started", nullable=False)

    assigned_to = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True, index=True)
    due_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    objective = relationship("Objective", back_populates="key_results")
