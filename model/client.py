from sqlalchemy import Column, Integer, String, Text, Date, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from core.database import Base

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    Project_name = Column(String(150), nullable=True)
    projects = relationship("Project", back_populates="client", cascade="all, delete-orphan")