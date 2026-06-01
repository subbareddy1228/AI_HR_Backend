# app/models/asset_insurance.py

from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class AssetInsurance(Base):
    __tablename__ = "asset_insurances"

    id = Column(Integer, primary_key=True, index=True)

    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)

    insurance_provider = Column(String(150), nullable=False)
    policy_number = Column(String(150), nullable=False, unique=True)

    coverage_amount = Column(Numeric(12, 2), nullable=False)
    premium_amount = Column(Numeric(12, 2), nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    asset = relationship("Asset")
