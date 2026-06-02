from pydantic import BaseModel

class FinancialYearCreate(BaseModel):
    start_month: str
    start_day: int
    end_month: str
    end_day: int
    period_type: str
    tax_year_alignment: str

class FinancialYearResponse(FinancialYearCreate):
    id: int
    current_year: str
    previous_year: str
    next_year: str
    is_active: bool

    class Config:
        orm_mode = True
