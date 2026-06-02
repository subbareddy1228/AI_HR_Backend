from sqlalchemy import Column, Integer, String
from core.database import Base

class PresentAddress(Base):
    __tablename__ = "present_address"

    id = Column(Integer, primary_key=True, index=True)
    address_line_1 = Column(String(100), nullable=False)
    address_line_2 = Column(String(100), nullable=True)
    city = Column(String(50), nullable=False)
    pincode = Column(String(6), nullable=False)
    state = Column(String(50), nullable=False)
    country = Column(String(50), default="India")
