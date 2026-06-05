from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


# ── KeyResult ──────────────────────────────────────────────────────────────────

class KeyResultBase(BaseModel):
    title:       str
    current:     float = 0
    target:      float
    unit:        Optional[str] = None
    is_inverse:  int = 0


class KeyResultCreate(KeyResultBase):
    pass


class KeyResultUpdate(BaseModel):
    title:       Optional[str]   = None
    current:     Optional[float] = None
    target:      Optional[float] = None
    unit:        Optional[str]   = None
    is_inverse:  Optional[int]   = None


class KeyResultResponse(KeyResultBase):
    id:           int
    objective_id: int
    created_at:   datetime
    model_config  = ConfigDict(from_attributes=True)


# ── Objective ──────────────────────────────────────────────────────────────────

class ObjectiveBase(BaseModel):
    objective: str
    owner:     str
    quarter:   str
    status:    str = "on-track"
    progress:  int = 0


class ObjectiveCreate(ObjectiveBase):
    key_results: List[KeyResultCreate] = []


class ObjectiveUpdate(BaseModel):
    objective:  Optional[str] = None
    owner:      Optional[str] = None
    quarter:    Optional[str] = None
    status:     Optional[str] = None
    progress:   Optional[int] = None


class ObjectiveResponse(ObjectiveBase):
    id:          int
    created_at:  datetime
    updated_at:  datetime
    key_results: List[KeyResultResponse] = []
    model_config = ConfigDict(from_attributes=True)
