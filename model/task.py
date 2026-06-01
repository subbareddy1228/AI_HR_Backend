from sqlalchemy import Column, Integer, String, Text, Date, Boolean
from sqlalchemy.sql import expression
from core.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    projected_minutes = Column(Integer, nullable=False, default=0)
    completed = Column(Boolean, server_default=expression.false(), nullable=False)
