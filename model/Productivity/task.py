from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("employee.id"), nullable=True)

    status = Column(String, default="Pending", index=True)
    due_date = Column(Date, nullable=True)

    #  COMPLETION TRACKING
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="tasks")
    team = relationship("Team", back_populates="tasks")

    assignee = relationship(
        "Employee",
        back_populates="tasks",
        foreign_keys=[assigned_to]
    )
