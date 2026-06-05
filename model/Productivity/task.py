from sqlalchemy import Column, Integer, String, DateTime, Text
from core.database import Base
from datetime import datetime


class ProductivityTask(Base):
    __tablename__ = "productivity_tasks"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(500), nullable=False)
    assignee    = Column(String(255), nullable=True)
    department  = Column(String(100), nullable=True)
    priority    = Column(String(20), default="Medium")    # Low / Medium / High / Critical
    status      = Column(String(50), default="To Do")     # To Do / In Progress / In Review / Done
    due_date    = Column(String(20), nullable=True)        # stored as ISO date string
    tags        = Column(Text, nullable=True)              # comma-separated
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
