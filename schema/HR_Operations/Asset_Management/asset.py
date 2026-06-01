from datetime import date
from pydantic import BaseModel, ConfigDict


# 🔹 Shared fields
class AssetBase(BaseModel):
    asset_name: str
    category: str
    make: str
    model: str
    serial_number: str
    purchase_date: date
    purchase_price: float
    depreciation_rate: int
    condition: str
    location: str
    department: str
    warranty_until: date | None = None


# 🔹 Create request
# Client should NOT control lifecycle status during creation
class AssetCreate(AssetBase):
    pass


# 🔹 Update request
class AssetUpdate(BaseModel):
    asset_name: str | None = None
    category: str | None = None
    make: str | None = None
    model: str | None = None
    purchase_price: float | None = None
    depreciation_rate: int | None = None
    condition: str | None = None
    location: str | None = None
    department: str | None = None
    warranty_until: date | None = None

    # Optional — only if you allow manual lifecycle updates
    status: str | None = None


# 🔹 Response schema
class AssetResponse(AssetBase):
    id: int
    status: str  # ✅ REQUIRED because service uses it

    model_config = ConfigDict(from_attributes=True)
