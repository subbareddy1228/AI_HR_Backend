from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
# Screenshot Model
class Screenshot(Base):
    __tablename__ = "screenshots"

    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Foreign keys
    employee_id = Column(Integer, ForeignKey("employee.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    employee = relationship("Employee", back_populates="screenshots")
    department = relationship("Department", back_populates="screenshots")
