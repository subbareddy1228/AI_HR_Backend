# app/schemas/asset_insurance.py

from pydantic import BaseModel
from datetime import date


class AssetInsuranceCreate(BaseModel):
    asset_id: int
    insurance_provider: str
    policy_number: str
    coverage_amount: float
    premium_amount: float
    start_date: date
    end_date: date


class AssetInsuranceResponse(AssetInsuranceCreate):
    id: int

    model_config = {"from_attributes": True}
