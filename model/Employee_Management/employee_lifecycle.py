from sqlalchemy import Column, Integer, String, Date, Text, DateTime
from datetime import datetime
from core.database import Base


class EmployeeLifecycleEvent(Base):
    __tablename__ = "employee_lifecycle_events"

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, nullable=False)
    event_type = Column(String(100))  # Promotion, Transfer, Confirmation, Resignation, Termination
    event_date = Column(Date)
    from_value = Column(String(255), nullable=True)
    to_value = Column(String(255), nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)