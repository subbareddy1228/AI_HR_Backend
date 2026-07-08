from sqlalchemy import Column, Integer, String, Date
from core.database import Base


class BasicDetails(Base):
    __tablename__ = "basic_details"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    last_name = Column(String(50), nullable=False)
    gender = Column(String(20), nullable=False)
    date_of_birth = Column(Date, nullable=False)
