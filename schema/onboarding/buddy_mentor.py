from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

from model.onboarding.buddy_mentor import (
    ProgramType, ProgramStatus, PairingStatus, CommunicationType
)



class AssignmentRuleCreate(BaseModel):
    rule_text:    str
    is_mandatory: bool = True
    weight_score: int  = 0


class AssignmentRuleOut(BaseModel):
    id:           int
    program_id:   int
    rule_text:    str
    is_mandatory: bool
    weight_score: int

    model_config = {"from_attributes": True}




class BuddyProgramCreate(BaseModel):
    program_name:     str
    program_type:     ProgramType
    description:      Optional[str]  = None
    department:       Optional[str]  = "All"
    location:         Optional[str]  = "All"
    start_date:       date
    end_date:         Optional[date] = None
    status:           ProgramStatus  = ProgramStatus.ACTIVE
    created_by:       str
    assignment_rules: Optional[List[AssignmentRuleCreate]] = []


class BuddyProgramUpdate(BaseModel):
    program_name: Optional[str]           = None
    program_type: Optional[ProgramType]   = None
    description:  Optional[str]           = None
    department:   Optional[str]           = None
    location:     Optional[str]           = None
    start_date:   Optional[date]          = None
    end_date:     Optional[date]          = None
    status:       Optional[ProgramStatus] = None


class BuddyProgramOut(BaseModel):
    id:               int
    program_name:     str
    program_type:     ProgramType
    description:      Optional[str]
    department:       Optional[str]
    location:         Optional[str]
    start_date:       date
    end_date:         Optional[date]
    status:           ProgramStatus
    created_by:       str
    created_on:       datetime
    assignment_rules: List[AssignmentRuleOut] = []

    model_config = {"from_attributes": True}


class BuddyProgramListOut(BaseModel):
    
    id:           int
    program_name: str
    program_type: ProgramType
    status:       ProgramStatus
    department:   Optional[str]
    location:     Optional[str]
    start_date:   date
    end_date:     Optional[date]
    total_pairs:  int   = 0
    active_pairs: int   = 0
    avg_rating:   Optional[float] = None

    model_config = {"from_attributes": True}




class BuddyPairingCreate(BaseModel):
    program_id:      int
    buddy_id:        int
    new_joiner_id:   int
    assignment_date: date
    match_score:     Optional[int]          = None
    status:          PairingStatus          = PairingStatus.ACTIVE


class BuddyPairingUpdate(BaseModel):
    last_checkin:   Optional[date]         = None
    progress:       Optional[int]          = Field(None, ge=0, le=100)
    feedback_score: Optional[float]        = Field(None, ge=0.0, le=5.0)
    status:         Optional[PairingStatus] = None


class BuddyPairingOut(BaseModel):
    id:                    int
    program_id:            int
    buddy_id:              int
    new_joiner_id:         int
    buddy_name:            Optional[str]   = None
    buddy_department:      Optional[str]   = None
    new_joiner_name:       Optional[str]   = None
    new_joiner_department: Optional[str]   = None
    match_score:           Optional[int]
    assignment_date:       date
    last_checkin:          Optional[date]
    progress:              int
    feedback_score:        Optional[float]
    status:                PairingStatus

    model_config = {"from_attributes": True}


class AutoMatchRequest(BaseModel):
    program_id:    int
    buddy_id:      int
    new_joiner_id: int


class AutoMatchOut(BaseModel):
    buddy_id:      int
    new_joiner_id: int
    match_score:   int
    match_reason:  str




class BuddyFeedbackCreate(BaseModel):
    pairing_id:                  int
    submitted_by:                str
    overall_rating:              int = Field(..., ge=1, le=5)
    responsiveness:              Optional[int] = Field(None, ge=1, le=5)
    knowledge_sharing:           Optional[int] = Field(None, ge=1, le=5)
    support:                     Optional[int] = Field(None, ge=1, le=5)
    communication:               Optional[int] = Field(None, ge=1, le=5)
    overall_comments:            Optional[str] = None
    responsiveness_comments:     Optional[str] = None
    knowledge_sharing_comments:  Optional[str] = None
    support_comments:            Optional[str] = None
    communication_comments:      Optional[str] = None


class BuddyFeedbackOut(BuddyFeedbackCreate):
    id:           int
    submitted_at: datetime

    model_config = {"from_attributes": True}




class BuddyCommunicationCreate(BaseModel):
    pairing_id:         int
    communication_type: CommunicationType
    date:               date
    duration_minutes:   Optional[int]  = None
    next_checkin_date:  Optional[date] = None
    topics_discussed:   Optional[str]  = None    # comma-separated
    follow_up_actions:  Optional[str]  = None    # comma-separated
    additional_notes:   Optional[str]  = None


class BuddyCommunicationOut(BuddyCommunicationCreate):
    id:          int
    recorded_at: datetime

    model_config = {"from_attributes": True}




class DeptDistribution(BaseModel):
    department: str
    count:      int


class LocDistribution(BaseModel):
    location: str
    count:    int


class ProgramAnalyticsOut(BaseModel):
    program_id:               int
    program_name:             str
    total_pairs:              int
    active_pairs:             int
    completed_pairs:          int
    completion_rate:          float           # percentage
    avg_rating:               Optional[float]
    avg_match_score:          Optional[float]
    feedback_count:           int
    satisfaction_score:       Optional[float]
    time_to_productivity_days: Optional[int]
    department_distribution:  List[DeptDistribution] = []
    location_distribution:    List[LocDistribution]  = []




class BuddyDashboardOut(BaseModel):
    total_programs:     int
    active_programs:    int
    total_pairs:        int
    active_pairs:       int
    available_buddies:  int
    avg_rating:         Optional[float]
    unassigned_joiners: int