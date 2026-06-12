from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime, date
from typing import Optional, List
from enum import Enum




class TicketCategory(str, Enum):
    PAYROLL_QUERIES          = "Payroll queries"
    LEAVE_ATTENDANCE         = "Leave and attendance issues"
    POLICY_CLARIFICATIONS    = "Policy clarifications"
    IT_ACCESS_ISSUES         = "IT access issues"
    DOCUMENT_REQUESTS        = "Document requests"
    REIMBURSEMENT_QUERIES    = "Reimbursement queries"
    PERSONAL_DATA_UPDATES    = "Personal data updates"
    GENERAL_HR_QUERIES       = "General HR queries"
    GRIEVANCES_COMPLAINTS    = "Grievances and complaints"


class TicketPriority(str, Enum):
    LOW    = "LOW"
    MEDIUM = "MEDIUM"
    HIGH   = "HIGH"
    URGENT = "URGENT"


class TicketStatus(str, Enum):
    OPEN        = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED    = "RESOLVED"
    CLOSED      = "CLOSED"




class HRHelpdeskCreate(BaseModel):
    title:         str                          
    category:      TicketCategory                
    description:   str                           
    priority:      TicketPriority = TicketPriority.MEDIUM   
    employee_id:   Optional[int]  = None         
    employee_name: Optional[str]  = None         
    due_date:      Optional[date] = None         




class HRHelpdeskUpdate(BaseModel):
    title:          Optional[str]            = None
    category:       Optional[TicketCategory] = None
    description:    Optional[str]            = None
    priority:       Optional[TicketPriority] = None
    status:         Optional[TicketStatus]   = None
    assigned_to:    Optional[int]            = None
    assigned_agent: Optional[str]            = None
    resolution:     Optional[str]            = None
    due_date:       Optional[date]           = None
    employee_name:  Optional[str]            = None




class TicketAssignPayload(BaseModel):
    assigned_to:    Optional[int] = None
    assigned_agent: Optional[str] = None    




class TicketResolvePayload(BaseModel):
    resolution: str




class HRHelpdeskResponse(BaseModel):
    id:             int
    title:          str
    category:       str
    description:    str
    priority:       str
    status:         str
    employee_id:    Optional[int]
    employee_name:  Optional[str]
    assigned_to:    Optional[int]
    assigned_agent: Optional[str]
    resolution:     Optional[str]
    resolved_at:    Optional[datetime]
    due_date:       Optional[date]
    created_at:     datetime
    updated_at:     datetime

    model_config = ConfigDict(from_attributes=True)




class HelpdeskStatCards(BaseModel):
    
    total_tickets:   int
    open:            int
    in_progress:     int
    resolved:        int
    high_priority:   int
    unassigned:      int
    todays_tickets:  int
    overdue:         int



class CategoryBreakdownItem(BaseModel):
    category: str
    count:    int


class CategoryBreakdownResponse(BaseModel):
    items: List[CategoryBreakdownItem]




class AgentPerformanceItem(BaseModel):
    agent_name:  str
    total:       int
    resolved:    int
    in_progress: int
    open:        int


class AgentPerformanceResponse(BaseModel):
    agents: List[AgentPerformanceItem]




class WeeklyReportResponse(BaseModel):
    week_start:         date
    week_end:           date
    tickets_created:    int
    tickets_resolved:   int
    tickets_closed:     int
    avg_resolution_hrs: float
    top_category:       Optional[str]
    unresolved_count:   int
    overdue_count:      int
    agent_breakdown:    List[AgentPerformanceItem]
    category_breakdown: List[CategoryBreakdownItem]
