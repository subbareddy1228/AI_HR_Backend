from sqlalchemy import Column, Integer, String, Date, Enum
from core.database import Base
import enum

class MaritalStatusEnum(enum.Enum):
    single = "single"
    married = "married"

class FamilyDetails(Base):
    __tablename__ = "family_details"

    id = Column(Integer, primary_key=True, index=True)
    marital_status = Column(Enum(MaritalStatusEnum), nullable=False)
    father_name = Column(String(50))
    father_phone = Column(String(15))
    father_dob = Column(Date)
    mother_name = Column(String(50))
    mother_phone = Column(String(15))
    mother_dob = Column(Date)
