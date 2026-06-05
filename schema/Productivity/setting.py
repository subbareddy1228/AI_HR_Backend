from pydantic import BaseModel
from typing import Optional

class SettingBase(BaseModel):
    name: str
    enabled: bool
    channel: Optional[str] = "in_app"

class SettingCreate(SettingBase):
    pass

class SettingRead(SettingBase):
    id: int

    class Config:
        from_attributes = True
