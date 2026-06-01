from sqlalchemy import Column, Integer, String, Float, Date, Time, Text, Boolean, Enum, TIMESTAMP, func
from core.database import Base
import enum
from typing import Optional, List


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    activity_type = Column(String, nullable=False)
    due_date = Column(Date, nullable=True)
    activity_time = Column(Time, nullable=True)
    remainder = Column(String, nullable=True)
    remainder_type = Column(String, nullable=True)
    owner = Column(String, nullable=True)
    guests = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    deals = Column(String, nullable=True)
    contacts = Column(String, nullable=True)
    companies = Column(String, nullable=True)
    created_date = Column(Date, nullable=True)
