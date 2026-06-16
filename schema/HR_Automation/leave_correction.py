from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class LeaveCorrectionRow(BaseModel):
   
    employee_id: int
    employee_code: str
    employee_name: str
    designation: Optional[str] = None
    business_unit: Optional[str] = None
    location: Optional[str] = None
    cost_center: Optional[str] = None
    department: Optional[str] = None
    leave_type: str             
    leave_type_code: str        
    month: int
    year: int
    opening: float = 0.0        
    activity: float = 0.0       
    correction: float = 0.0     
    closing: float = 0.0        

    model_config = ConfigDict(from_attributes=True)


class LeaveCorrectionSave(BaseModel):
    
    employee_id: int
    leave_type_code: str       
    month: int
    year: int
    correction: float           
    remarks: Optional[str] = None


class LeaveCorrectionBulkSave(BaseModel):
    
    month: int
    year: int
    leave_type_code: str
    rows: List[LeaveCorrectionSave]


class LeaveTypeOption(BaseModel):
    
    code: str                   
    label: str                  
    short_name: str             


class FilterOptions(BaseModel):
    
    business_units: List[str]
    locations: List[str]
    cost_centers: List[str]
    departments: List[str]
    leave_types: List[LeaveTypeOption]