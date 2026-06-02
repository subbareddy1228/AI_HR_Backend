from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime


# CLIENT SCHEMAS
class ClientBase(BaseModel):
    name: str = Field(..., max_length=150)
    Project_name: Optional[str] = Field(None, max_length=150) 


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True 
