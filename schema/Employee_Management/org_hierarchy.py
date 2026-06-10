
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
 
 

class DepartmentBase(BaseModel):
    name: str
    code: Optional[str] = None
    parent_department_id: Optional[int] = None
    head_employee_id: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = True
 
 
class DepartmentCreate(DepartmentBase):
    pass
 
 
class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    parent_department_id: Optional[int] = None
    head_employee_id: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None
 
 
class DepartmentResponse(DepartmentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
 
    model_config = ConfigDict(from_attributes=True)
 
 
class DepartmentTree(DepartmentResponse):
    
    children: List['DepartmentTree'] = []
 
    model_config = ConfigDict(from_attributes=True)
 
 
DepartmentTree.model_rebuild()
 
 

class OrgHierarchyStats(BaseModel):
  
    total_departments: int
    total_employees: int
    avg_span_of_control: float
    pending_changes: int
 
 

class ReportingRelationshipBase(BaseModel):
    employee_id: int
    manager_id: int
    relationship_type: str = "DIRECT"   
    effective_date: Optional[datetime] = None
    is_active: Optional[bool] = True
 
 
class ReportingRelationshipCreate(ReportingRelationshipBase):
    pass
 
 
class ReportingRelationshipUpdate(BaseModel):
    manager_id: Optional[int] = None
    relationship_type: Optional[str] = None
    effective_date: Optional[datetime] = None
    is_active: Optional[bool] = None
 
 
class ReportingRelationshipResponse(ReportingRelationshipBase):
    id: int
    created_at: Optional[datetime] = None
 
    model_config = ConfigDict(from_attributes=True)
 
 
class ReportingRelationshipSummary(BaseModel):
    
    direct_reports: int
    dotted_line_reports: int
    matrix_reports: int
    individual_contributors: int
 
 

 
class HierarchyHealth(BaseModel):
    
    reporting_completeness_pct: float
    overloaded_managers: int
    underloaded_managers: int
    manager_to_ic_ratio: str            
 
class SpanOfControlItem(BaseModel):
    manager_id: int
    manager_name: str
    direct_report_count: int
    status: str                         
 
 
class SpanOfControlAnalytics(BaseModel):
    average_span: float
    overloaded_count: int
    underloaded_count: int
    details: List[SpanOfControlItem]
 
 

 
class HierarchyChangeRequestCreate(BaseModel):
    employee_id: int
    change_type: str                   
    from_value: Optional[str] = None
    to_value: str
    remarks: Optional[str] = None
    requested_by: int
 
 
class HierarchyChangeRequestUpdate(BaseModel):
    status: str                        
    remarks: Optional[str] = None
    approved_by: Optional[int] = None
 
 
class HierarchyChangeRequestResponse(BaseModel):
    id: int
    employee_id: int
    change_type: str
    from_value: Optional[str] = None
    to_value: str
    status: str
    remarks: Optional[str] = None
    requested_by: int
    approved_by: Optional[int] = None
    created_at: Optional[datetime] = None
 
    model_config = ConfigDict(from_attributes=True)
 
 

 
class HierarchyHistoryResponse(BaseModel):
    id: int
    employee_id: int
    department_id: Optional[int] = None
    manager_id: Optional[int] = None
    designation: Optional[str] = None
    location: Optional[str] = None
    effective_from: datetime
    effective_to: Optional[datetime] = None
    changed_by: Optional[int] = None
    created_at: Optional[datetime] = None
 
    model_config = ConfigDict(from_attributes=True)
 
 

 
class DepartmentLocationView(BaseModel):
    department_id: int
    department_name: str
    location: Optional[str]
    employee_count: int
    head_employee_id: Optional[int]