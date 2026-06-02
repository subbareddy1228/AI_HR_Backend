from pydantic import BaseModel, Field

class StatutoryBase(BaseModel):
    aadhaar_number: str = Field(..., min_length=12, max_length=12)
    pan_number: str = Field(..., min_length=10, max_length=10)
    uan_number: str | None = None
    esi_number: str | None = None

class StatutoryCreate(StatutoryBase):
    pass

class StatutoryResponse(StatutoryBase):
    id: int

    class Config:
        orm_mode = True
