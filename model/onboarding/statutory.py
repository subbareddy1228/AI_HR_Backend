from sqlalchemy import Column, Integer, String
from core.database import Base

class StatutoryDetails(Base):
    __tablename__ = "statutory_details"

    id = Column(Integer, primary_key=True, index=True)
    aadhaar_number = Column(String(12), nullable=False)
    pan_number = Column(String(10), nullable=False)
    uan_number = Column(String(12))
    esi_number = Column(String(20))
