from sqlalchemy import Column, Integer, String, Boolean
from core.database import Base


class ContactDetails(Base):
    __tablename__ = "contact_details"

    id = Column(Integer, primary_key=True, index=True)
    mobile = Column(String(10), nullable=False)
    email = Column(String(100), nullable=False)
    home_phone = Column(String(15))
    emergency_contact = Column(String(15))
    mobile_verified = Column(Boolean, default=False)
