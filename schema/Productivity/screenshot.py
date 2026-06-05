from pydantic import BaseModel, computed_field
from datetime import datetime, date
from typing import List

class ScreenshotResponse(BaseModel):
    id: int
    image_path: str
    timestamp: datetime
    

    @computed_field
    @property
    def date(self) -> date:
        return self.timestamp.date()

    class Config:
        from_attributes = True


class ScreenshotPaginationResponse(BaseModel):
    items: List[ScreenshotResponse]
    hasMore: bool
    page: int
    limit: int