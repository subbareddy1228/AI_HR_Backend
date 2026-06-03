from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class ExitManagement(Base):
    __tablename__ = "exit_management"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    resignation_date = Column(Date, nullable=False)
    last_working_date = Column(Date, nullable=True)
    exit_type = Column(String(50), nullable=False)          # RESIGNATION | TERMINATION | RETIREMENT | ABSCONDING
    reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, server_default="INITIATED")  # INITIATED | IN_PROGRESS | COMPLETED | CANCELLED
    exit_interview_done = Column(String(10), nullable=False, server_default="NO")  # YES | NO
    clearance_status = Column(String(50), nullable=False, server_default="PENDING")  # PENDING | PARTIAL | COMPLETED
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
