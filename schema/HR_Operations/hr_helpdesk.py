from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ---------- Enums-as-literals (kept as plain strings for flexibility) ----------

CATEGORIES = [
    "Payroll queries",
    "Leave and attendance issues",
    "Policy clarifications",
    "IT access issues",
    "Document requests",
    "Reimbursement queries",
    "Personal data updates",
    "General HR queries",
    "Grievances and complaints",
]

PRIORITIES = ["Low", "Medium", "High"]

STATUSES = ["Open", "In-Progress", "Resolved", "Closed"]

AGENTS = ["John HR", "Priya Kumar", "IT Support", "Admin Team", "Finance Team"]


# ---------- Request schemas ----------

class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category: str
    priority: str = "Medium"
    employee_name: Optional[str] = None
    description: str = Field(..., min_length=1)


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    employee_name: Optional[str] = None
    description: Optional[str] = None
    assigned_agent: Optional[str] = None


class TicketStart(BaseModel):
    assigned_agent: str


# ---------- Response schemas ----------

class TicketOut(BaseModel):
    id: int
    title: str
    category: str
    priority: str
    status: str
    employee_name: Optional[str] = None
    description: str
    assigned_agent: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    total: int
    tickets: List[TicketOut]


class StatsResponse(BaseModel):
    total_tickets: int
    open: int
    in_progress: int
    resolved: int
    high_priority: int
    unassigned: int
    today_tickets: int
    overdue: int


class CategoryBreakdownItem(BaseModel):
    category: str
    count: int


class AgentPerformanceItem(BaseModel):
    agent: str
    total: int
    resolved: int
    avg_resolution_hours: float