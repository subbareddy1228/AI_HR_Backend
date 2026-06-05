from sqlalchemy import Column, Integer, String, Boolean, Date
from core.database import Base
# Notification Model
class ProductivityNotification(Base):
    __tablename__ = "productivity_notifications"
    id = Column(Integer, primary_key=True, index=True)
    message = Column(String, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(Date)
