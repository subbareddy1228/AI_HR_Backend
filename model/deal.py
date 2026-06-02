from sqlalchemy import Column, Integer, String, Float, Date, Time, Text, Boolean, Enum, TIMESTAMP, func
from core.database import Base
import enum
from typing import Optional, List


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    deal_name = Column(String, nullable=False)
    pipeline = Column(String, nullable=True)
    status = Column(String, nullable=True)
    deal_value = Column(Float, nullable=True)
    currency = Column(String, nullable=True)
    period = Column(String, nullable=True)
    period_value = Column(Integer, nullable=True)
    contact = Column(String, nullable=True)
    project = Column(String, nullable=True)
    due_date = Column(Date, nullable=True)
    expected_closing_date = Column(Date, nullable=True)
    assignee = Column(String, nullable=True)
    tags = Column(String, nullable=True)
    followup_date = Column(Date, nullable=True)
    source = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Deal(id={self.id}, deal_name='{self.deal_name}', status='{self.status}')>"


