# FILE 6 of 18 | model/Payroll/statutory_compliance.py
# Model: StatutoryConfig
# Table: statutory_configs

from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Text
from core.database import Base
from datetime import datetime


class StatutoryConfig(Base):
    __tablename__ = "statutory_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_name = Column(String(100), unique=True, default="default")
    pf_wage_limit = Column(Numeric(10, 2), default=15000)
    esi_wage_limit = Column(Numeric(10, 2), default=21000)
    pf_employee_rate = Column(Float, default=12.0)
    pf_employer_rate = Column(Float, default=12.0)
    esi_employee_rate = Column(Float, default=0.75)
    esi_employer_rate = Column(Float, default=3.25)
    lwf_employee = Column(Numeric(10, 2), default=25)
    lwf_employer = Column(Numeric(10, 2), default=75)
    professional_tax_slab = Column(Text, nullable=True)  # JSON slab config
    updated_at = Column(DateTime, default=datetime.utcnow)
