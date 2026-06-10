
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class LeadStatus(str, Enum):
    Contacted = "Contacted"
    Not_Contacted = "Not_Contacted"
    Closed = "Closed"
    Lost = "Lost"


class Visibility(str, Enum):
    Private = "Private"
    Team = "Team"
    Public = "Public"


class LeadBase(BaseModel):
    name: str
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    value: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = None

    status: LeadStatus = LeadStatus.Not_Contacted
    visibility: Visibility = Visibility.Private

    source: Optional[str] = None
    industry: Optional[str] = None
    owner: Optional[str] = None

    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if v == "Not Contacted":
            return "Not_Contacted"
        return v

    @field_validator("visibility", mode="before")
    @classmethod
    def normalize_visibility(cls, v: Any) -> Any:
        if v is None:
            return v
        s = str(v).lower()
        if s == "private":
            return "Private"
        if s == "public":
            return "Public"
        if s in ("team", "select_people"):
            return "Team"
        return v

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return v if v >= 0 else None
        if isinstance(v, str):
            cleaned = "".join(c for c in v if c.isdigit() or c in "-.")
            if not cleaned:
                return None
            try:
                n = int(float(cleaned))
                return n if n >= 0 else None
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return []


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    value: Optional[int] = Field(default=None, ge=0)
    currency: Optional[str] = None
    status: Optional[LeadStatus] = None
    visibility: Optional[Visibility] = None
    source: Optional[str] = None
    industry: Optional[str] = None
    owner: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: Any) -> Any:
        if v is None:
            return v
        if v == "Not Contacted":
            return "Not_Contacted"
        return v

    @field_validator("visibility", mode="before")
    @classmethod
    def normalize_visibility(cls, v: Any) -> Any:
        if v is None:
            return v
        s = str(v).lower()
        if s == "private":
            return "Private"
        if s == "public":
            return "Public"
        if s in ("team", "select_people"):
            return "Team"
        return v

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v: Any) -> Any:
        if v is None or v == "":
            return None
        if isinstance(v, int):
            return v if v >= 0 else None
        if isinstance(v, str):
            cleaned = "".join(c for c in v if c.isdigit() or c in "-.")
            if not cleaned:
                return None
            try:
                n = int(float(cleaned))
                return n if n >= 0 else None
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def coerce_tags(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return None


class LeadRead(LeadBase):
    id: int
    created_at: datetime
    updated_at: datetime
    