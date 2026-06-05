from sqlalchemy import Column, Integer, String, Boolean, Date
from app.core.database import Base
# Notification Model
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(Date)
