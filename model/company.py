from sqlalchemy import Column, Integer, String, Float, Text
from core.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)

    company_name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    phone_number2 = Column(String, nullable=True)

    location = Column(String, nullable=True)
    address = Column(String, nullable=True)
    country = Column(String, nullable=True)
    state = Column(String, nullable=True)
    city = Column(String, nullable=True)
    zipcode = Column(String, nullable=True)

    rating = Column(Float, nullable=True)
    logo = Column(String, nullable=True)

    fax = Column(String, nullable=True)
    website = Column(String, nullable=True)
    owner = Column(String, nullable=True)

    tags = Column(String, nullable=True)
    deals = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    source = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    language = Column(String, nullable=True)

    about = Column(Text, nullable=True)
    contact = Column(String, nullable=True)

    facebook = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    skype = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)
    instagram = Column(String, nullable=True)

    visibility = Column(String, default="private")
    status = Column(String, nullable=True)
