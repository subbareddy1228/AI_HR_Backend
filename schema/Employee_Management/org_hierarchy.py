# # FILE 6 of 12 | schema/Employee_Management/org_hierarchy.py
# # Schemas: DepartmentBase, DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTree

# from pydantic import BaseModel, ConfigDict
# from typing import Optional, List
# from datetime import datetime


# class DepartmentBase(BaseModel):
#     name: str
#     code: Optional[str] = None
#     parent_department_id: Optional[int] = None
#     head_employee_id: Optional[int] = None
#     description: Optional[str] = None
#     is_active: Optional[bool] = True


# class DepartmentCreate(DepartmentBase):
#     pass


# class DepartmentUpdate(BaseModel):
#     name: Optional[str] = None
#     code: Optional[str] = None
#     parent_department_id: Optional[int] = None
#     head_employee_id: Optional[int] = None
#     description: Optional[str] = None
#     is_active: Optional[bool] = None


# class DepartmentResponse(DepartmentBase):
#     id: int
#     created_at: Optional[datetime] = None

#     model_config = ConfigDict(from_attributes=True)


# class DepartmentTree(DepartmentResponse):
#     children: List['DepartmentTree'] = []

#     model_config = ConfigDict(from_attributes=True)


# DepartmentTree.model_rebuild()





# schema/Employee_Management/org_hierarchy.py
# Schemas: DepartmentBase, DepartmentCreate, DepartmentUpdate, DepartmentResponse, DepartmentTree

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
    cost_center: Optional[str] = None
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
    cost_center: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(DepartmentBase):
    id: int
    span_of_control: Optional[int] = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DepartmentTree(DepartmentResponse):
    """Recursive nested tree node for org chart rendering."""
    children: List['DepartmentTree'] = []

    model_config = ConfigDict(from_attributes=True)


DepartmentTree.model_rebuild()
