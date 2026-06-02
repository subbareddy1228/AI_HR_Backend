from sqlalchemy import Column, Integer, String, Date, Text
from core.database import Base

class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(String(255), nullable=False)
    company_type = Column(String(100))
    company_website = Column(String(255))
    email = Column(String(255))

    registration_number = Column(String(100))
    tax_id = Column(String(100))
    vat_gst_number = Column(String(100))

    industry = Column(String(150))
    legal_entity_name = Column(String(255))

    year_founded = Column(Integer)
    registration_date = Column(Date)
    registration_authority = Column(String(255))

    incorporation_number = Column(String(100))
    phone = Column(String(50))
    address = Column(Text)
    about_company = Column(Text)

    logo_path = Column(String(255))
