from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class ManualAttendanceRow(BaseModel):
   
    employee_id: int
    employee_code: str
    employee_name: str
    business_unit: Optional[str] = None
    location: Optional[str] = None
    cost_center: Optional[str] = None
    department: Optional[str] = None
    P: int = 0    
    A: int = 0   
    H: int = 0    
    W: int = 0    
    CO: int = 0   
    CL: int = 0   
    LW: int = 0   

    model_config = ConfigDict(from_attributes=True)


class ManualAttendanceSave(BaseModel):
    
    employee_id: int
    month: int         
    year: int
    P: int = 0
    A: int = 0
    H: int = 0
    W: int = 0
    CO: int = 0
    CL: int = 0
    LW: int = 0
    remarks: Optional[str] = None


class ManualAttendanceBulkSave(BaseModel):
   
    month: int
    year: int
    rows: List[ManualAttendanceSave]


class ManualAttendanceUploadRow(BaseModel):
    
    employee_code: str
    P: int = 0
    A: int = 0
    H: int = 0
    W: int = 0
    CO: int = 0
    CL: int = 0
    LW: int = 0
    remarks: Optional[str] = None


class ManualAttendanceUpload(BaseModel):
    
    month: int
    year: int
    rows: List[ManualAttendanceUploadRow]


class FilterOptions(BaseModel):
    
    business_units: List[str]
    locations: List[str]
    cost_centers: List[str]
    departments: List[str]