

from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, field_validator


VALID_STATUSES    = {"Active", "Draft", "Archived", "Expired"}
VALID_CATEGORIES  = {
    "HR Policies", "Compliance", "IT Policies",
    "Finance", "Operations", "Legal", "Other"
}


class PolicyBase(BaseModel):
    title:          str
    category:       str
    version:        str
    effective_date: date
    description:    Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    title:          Optional[str]   = None
    category:       Optional[str]   = None
    version:        Optional[str]   = None
    effective_date: Optional[date]  = None
    description:    Optional[str]   = None
    status:         Optional[str]   = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v and v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v and v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}")
        return v


class PolicyResponse(PolicyBase):
    id:                     int
    tenant_id:              int
    status:                 str
    document_path:          Optional[str]   = None
    document_original_name: Optional[str]   = None
    document_size_bytes:    Optional[int]   = None
    created_at:             datetime
    updated_at:             datetime        

    model_config = {"from_attributes": True}


class PolicyListResponse(BaseModel):
    policies:   List[PolicyResponse]
    total:      int
