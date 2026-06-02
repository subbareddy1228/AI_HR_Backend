from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from core.database import Base
from datetime import datetime


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    workflow_name = Column(String(255), unique=True, nullable=False)
    workflow_type = Column(String(100), nullable=False)  # Leave Approval/Expense Approval/Exit/Transfer/Promotion/Custom
    steps = Column(JSON, nullable=True)  # [{step_no, role, action}, ...]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    reference_type = Column(String(100), nullable=True)  # leave_request/exit/transfer/etc.
    reference_id = Column(Integer, nullable=True)
    current_step = Column(Integer, default=1)
    status = Column(String(50), default="Pending")  # Pending/In Progress/Approved/Rejected/Cancelled
    initiated_by = Column(String(100), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
