from sqlalchemy import Column, Integer, String
from core.database import Base

class PermanentAddress(Base):
    __tablename__ = "permanent_addresses"

    id = Column(Integer, primary_key=True, index=True)
    address_line_1 = Column(String(255), nullable=False)
    address_line_2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=False)
    pincode = Column(String(6), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(100), default="India")
