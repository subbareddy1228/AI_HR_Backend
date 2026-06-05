from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

# Enums for Alert Priority and Status
class AlertPriority(str, enum.Enum):
    critical = "critical"
    warning = "warning"
    info = "info"
    success = "success"

class AlertStatus(str, enum.Enum):
    active = "active"
    dismissed = "dismissed"
    resolved = "resolved"
# Alert Model
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employee.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Enum(AlertPriority), nullable=False, default=AlertPriority.info)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.active)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    employee = relationship("Employee", back_populates="alerts")
