from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime


class Objective(Base):
    __tablename__ = "productivity_objectives"

    id            = Column(Integer, primary_key=True, index=True)
    objective     = Column(String(500), nullable=False)
    owner         = Column(String(255), nullable=False)
    quarter       = Column(String(20), nullable=False)         # e.g. "Q2 2025"
    status        = Column(String(50), default="on-track")    # on-track / at-risk / behind / completed
    progress      = Column(Integer, default=0)                 # 0-100
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    key_results   = relationship("KeyResult", back_populates="objective", cascade="all, delete-orphan")


class KeyResult(Base):
    __tablename__ = "productivity_key_results"

    id            = Column(Integer, primary_key=True, index=True)
    objective_id  = Column(Integer, ForeignKey("productivity_objectives.id"), nullable=False)
    title         = Column(String(500), nullable=False)
    current       = Column(Float, default=0)
    target        = Column(Float, nullable=False)
    unit          = Column(String(50), nullable=True)
    is_inverse    = Column(Integer, default=0)   # 1 = lower is better (e.g. churn)
    created_at    = Column(DateTime, default=datetime.utcnow)

    objective     = relationship("Objective", back_populates="key_results")
