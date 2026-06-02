from sqlalchemy import Column, Integer, String, Date, Boolean
from core.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)

    # BASIC
    name = Column(String, nullable=False)
    last_name = Column(String, nullable=True)
    job_title = Column(String, nullable=False)

    # COMPANY
    company_name = Column(String, nullable=False)

    # CONTACT DETAILS
    email = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    phone_number2 = Column(String, nullable=True)
    fax = Column(String, nullable=True)

    # BUSINESS
    deals = Column(String, nullable=True)
    dob = Column(Date, nullable=True)
    ratings = Column(String, nullable=True)
    owner = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    language = Column(String, nullable=True)

    # TAGS STORED AS CSV
    tags = Column(String, nullable=True)

    # SOURCE
    source = Column(String, nullable=True)

    # ADDRESS
    location = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    # SOCIAL LINKS
    facebook = Column(String, nullable=True)
    twitter = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    instagram = Column(String, nullable=True)
    skype = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # ACCESS
    access_level = Column(String, nullable=True)
    department = Column(String, nullable=True)

    allow_email_access = Column(Boolean, default=False)
    allow_phone_access = Column(Boolean, default=False)
    allow_data_export = Column(Boolean, default=False)

    # PROFILE PHOTO PATH
    profile_photo = Column(String, nullable=True)
