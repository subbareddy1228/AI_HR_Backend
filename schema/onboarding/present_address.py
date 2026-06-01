from pydantic import BaseModel, Field

class PresentAddressBase(BaseModel):
    address_line_1: str = Field(..., max_length=100)
    address_line_2: str | None = None
    city: str = Field(..., max_length=50)
    pincode: str = Field(..., min_length=6, max_length=6)
    state: str
    country: str = "India"

class PresentAddressCreate(PresentAddressBase):
    pass

class PresentAddressResponse(PresentAddressBase):
    id: int

    class Config:
        orm_mode = True
