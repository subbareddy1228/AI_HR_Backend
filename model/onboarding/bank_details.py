from sqlalchemy import Column, Integer, String
from core.database import Base

class BankDetails(Base):
    __tablename__ = "bank_details"
    id = Column(Integer, primary_key=True, index=True)
    bank_name = Column(String(50), nullable=False)
    ifsc_code = Column(String(11), nullable=False)
    account_number = Column(String(20), nullable=False)
    account_holder_name = Column(String(50), nullable=False)
