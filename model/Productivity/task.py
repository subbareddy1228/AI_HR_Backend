from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from core.database import Base

class ProductivityTask(Base):
    __tablename__ = "productivity_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)

    project_id = Column(Integer, ForeignKey("productivity_projects.id"), nullable=True)

    status = Column(String, default="Pending", index=True)
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("ProductivityProject", back_populates="tasks")

