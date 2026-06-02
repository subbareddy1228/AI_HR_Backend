from pydantic import BaseModel

class LocalizationCreate(BaseModel):
    default_language: str
    default_timezone: str
    date_format: str
    time_format: str
    number_format: str
    decimal_places: int
    currency_format: str
    first_day_of_week: str

class LocalizationResponse(LocalizationCreate):
    id: int
    is_active: bool
    class Config:
        from_attributes = True
