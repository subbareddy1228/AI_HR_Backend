from sqlalchemy import Column, Integer, String, Text, Date
from sqlalchemy.orm import relationship
from app.core.database import Base
# Project Model
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String, default="Active")

    # relationship with Task
    tasks = relationship("Task", back_populates="project")
