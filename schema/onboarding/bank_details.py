from pydantic import BaseModel, Field

class BankDetailsCreate(BaseModel):
    bank_name: str = Field(..., max_length=50)
    ifsc_code: str = Field(..., min_length=11, max_length=11)
    account_number: str = Field(..., max_length=20)
    account_holder_name: str = Field(..., max_length=50)

class BankDetailsResponse(BankDetailsCreate):
    id: int
    class Config:
        orm_mode = True
