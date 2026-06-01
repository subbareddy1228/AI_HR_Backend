from sqlalchemy import Column, Integer, String
from core.database import Base

class PersonalInfo(Base):
    __tablename__ = "personal_info"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    blood_group = Column(String)
    passport_number = Column(String)
    driving_license_number = Column(String)
