from sqlalchemy import Column, Integer, String, Boolean
from core.database import Base

class LocalizationPreference(Base):
    __tablename__ = "localization_preferences"
    id = Column(Integer, primary_key=True)
    default_language = Column(String)
    default_timezone = Column(String)
    date_format = Column(String)
    time_format = Column(String)
    number_format = Column(String)
    decimal_places = Column(Integer)
    currency_format = Column(String)
    first_day_of_week = Column(String)
    is_active = Column(Boolean, default=True)
