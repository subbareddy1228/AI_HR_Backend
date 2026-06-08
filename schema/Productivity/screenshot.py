from pydantic import BaseModel
from datetime import datetime, date
from typing import List


class ScreenshotResponse(BaseModel):
    id: int
    image_path: str
    timestamp: datetime
    date: date

    class Config:
        from_attributes = True


class ScreenshotPaginationResponse(BaseModel):
    items: List[ScreenshotResponse]
    hasMore: bool
    page: int
    limit: int