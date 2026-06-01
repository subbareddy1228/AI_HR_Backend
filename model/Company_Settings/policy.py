from sqlalchemy import Column, Integer, String, Date, Text
from core.database import Base

class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    version = Column(String(20), nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(String(50), default="Draft")
    description = Column(Text)
    document_path = Column(String(255))
