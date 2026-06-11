from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime




class ProbationKPISchema(BaseModel):
    totalEmployees:  int
    inProgress:      int
    atRisk:          int
    endingThisWeek:  int
    completed:       int
    highRisk:        int


class ProbationEmployeeSchema(BaseModel):
    
    id:               int
    employeeId:       str        
    name:             str
    designation:      Optional[str]
    department:       Optional[str]
    location:         Optional[str]

    
    probationStatus:  str
    extensionCount:   int       

    
    progressPercent:  int

    
    riskLevel:        str

    
    milestone30Done:  bool
    milestone60Done:  bool
    milestone90Done:  bool
    finalDone:        bool
    nextReviewDate:   Optional[str]

    
    daysRemaining:    int
    probationEndDate: Optional[str]

    
    currentRating:    Optional[str]  

    
    probationStartDate: Optional[str]
    joiningDate:        Optional[str]
    confirmationId:     Optional[int]



class ProbationAddEmployeeSchema(BaseModel):
    employee_id:          int
    probation_start_date: date
    probation_end_date:   date
    reviewed_by:          Optional[int] = None
    remarks:              Optional[str] = None



class ProbationStatusUpdateSchema(BaseModel):
    status:             Optional[str]  = None   
    performance_rating: Optional[str]  = None
    extended_till:      Optional[date] = None
    confirmation_date:  Optional[date] = None
    remarks:            Optional[str]  = None



class ProbationBulkActionSchema(BaseModel):
    confirmation_ids: List[int]
    action:           str    




class ProbationMilestoneSchema(BaseModel):
    confirmation_id:  int
    milestone:        str    
    rating:           Optional[str] = None
    remarks:          Optional[str] = None




class ProbationReportSchema(BaseModel):
    period:               str
    totalOnProbation:     int
    confirmed:            int
    extended:             int
    terminated:           int
    confirmationRate:     float
    avgProbationDays:     float
    byDepartment:         List[dict]
    byRiskLevel:          dict
    byRating:             dict