from pydantic import BaseModel, Field

class AddressCreate(BaseModel):
    address_line_1: str = Field(..., max_length=255)
    address_line_2: str | None = None
    city: str
    pincode: str = Field(..., min_length=6, max_length=6)
    state: str
    country: str = "India"

class AddressResponse(AddressCreate):
    id: int

    class Config:
        from_attributes = True
