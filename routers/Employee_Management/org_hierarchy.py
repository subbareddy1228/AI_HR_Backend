from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
 
from core.database import get_db
from core.dependencies import get_current_user, require_roles
# Role model: 'admin' is a strict superset of 'hr_admin' — anything hr_admin can
# do, admin can also do (admin = company owner, hr_admin = dedicated HR operator).
# Keep this true for any new route: if you gate something to ["...", "hr_admin"],
# include "admin" in that same list too, unless the action is intentionally
# owner-only/destructive (e.g. deleting the company profile), in which case
# gate it to ["admin"] alone and leave hr_admin out on purpose.
from model.models import User
from model.Employee_Management.org_hierarchy import (
    Department,
    ReportingRelationship,
    HierarchyChangeRequest,
    HierarchyHistory,
)
from model.Employee_Management.employee_master import EmployeeMaster
from model.onboarding.employee import Employee
from schema.Employee_Management.org_hierarchy import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    DepartmentTree,
    OrgHierarchyStats,
    ReportingRelationshipCreate,
    ReportingRelationshipUpdate,
    ReportingRelationshipResponse,
    ReportingRelationshipSummary,
    HierarchyHealth,
    SpanOfControlAnalytics,
    SpanOfControlItem,
    HierarchyChangeRequestCreate,
    HierarchyChangeRequestUpdate,
    HierarchyChangeRequestResponse,
    HierarchyHistoryResponse,
    DepartmentLocationView,
)
from datetime import datetime
 
router = APIRouter(prefix="/org-hierarchy", tags=["Org Hierarchy"])
 

 
def _build_tree(dept: Department, dept_map: dict) -> DepartmentTree:
    node = DepartmentTree.model_validate(dept)
    for child in dept_map.get(dept.id, []):
        node.children.append(_build_tree(child, dept_map))
    return node
 

@router.get("/stats", response_model=OrgHierarchyStats)
def get_org_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    total_departments = db.execute(
        select(func.count()).where(Department.is_active == True)
    ).scalar_one()
 
    total_employees = db.execute(
        select(func.count()).select_from(Employee)
    ).scalar_one()
 
    pending_changes = db.execute(
        select(func.count()).where(HierarchyChangeRequest.status == "PENDING")
    ).scalar_one()
 

    manager_counts = db.execute(
        select(ReportingRelationship.manager_id, func.count().label("cnt"))
        .where(
            ReportingRelationship.relationship_type == "DIRECT",
            ReportingRelationship.is_active == True,
        )
        .group_by(ReportingRelationship.manager_id)
    ).all()
 
    if manager_counts:
        avg_span = sum(r.cnt for r in manager_counts) / len(manager_counts)
    else:
        avg_span = 0.0
 
    return OrgHierarchyStats(
        total_departments=total_departments,
        total_employees=total_employees,
        avg_span_of_control=round(avg_span, 1),
        pending_changes=pending_changes,
    )
 
@router.post("/departments", response_model=DepartmentResponse, status_code=201)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    existing = db.execute(
        select(Department).where(Department.name == payload.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Department '{payload.name}' already exists.")
    if payload.parent_department_id:
        parent = db.get(Department, payload.parent_department_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent department not found.")
    obj = Department(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
 
 
@router.get("/departments", response_model=List[DepartmentResponse])
def list_departments(
    is_active: Optional[bool] = Query(None),
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Department)
    if is_active is not None:
        stmt = stmt.where(Department.is_active == is_active)
    if location:
        stmt = stmt.where(Department.location.ilike(f"%{location}%"))
    return db.execute(stmt).scalars().all()
 
 
@router.get("/departments/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = db.get(Department, department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found.")
    return obj
 
 
@router.put("/departments/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    obj = db.get(Department, department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found.")
    if payload.parent_department_id and payload.parent_department_id == department_id:
        raise HTTPException(status_code=400, detail="A department cannot be its own parent.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj
 
 
@router.delete("/departments/{department_id}", status_code=204)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    obj = db.get(Department, department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Department not found.")
    children = db.execute(
        select(func.count()).where(Department.parent_department_id == department_id)
    ).scalar_one()
    if children > 0:
        raise HTTPException(status_code=400, detail="Cannot delete a department that has sub-departments.")
    db.delete(obj)
    db.commit()
 

@router.get("/tree", response_model=List[DepartmentTree])
def get_org_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full nested org chart tree — used by the Visual Org Chart section."""
    all_depts = db.execute(
        select(Department).where(Department.is_active == True)
    ).scalars().all()
 
    dept_map = {}
    roots = []
    for d in all_depts:
        if d.parent_department_id is None:
            roots.append(d)
        else:
            dept_map.setdefault(d.parent_department_id, []).append(d)
 
    return [_build_tree(r, dept_map) for r in roots]
 
 
@router.get("/tree/{department_id}", response_model=DepartmentTree)
def get_dept_subtree(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sub-tree from a specific department — used for drill-down."""
    root = db.get(Department, department_id)
    if not root:
        raise HTTPException(status_code=404, detail="Department not found.")
    all_depts = db.execute(
        select(Department).where(Department.is_active == True)
    ).scalars().all()
    dept_map = {}
    for d in all_depts:
        if d.parent_department_id is not None:
            dept_map.setdefault(d.parent_department_id, []).append(d)
    return _build_tree(root, dept_map)
 

@router.get("/reporting-relationships/summary", response_model=ReportingRelationshipSummary)
def get_reporting_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    direct = db.execute(
        select(func.count()).where(
            ReportingRelationship.relationship_type == "DIRECT",
            ReportingRelationship.is_active == True,
        )
    ).scalar_one()
 
    dotted = db.execute(
        select(func.count()).where(
            ReportingRelationship.relationship_type == "DOTTED_LINE",
            ReportingRelationship.is_active == True,
        )
    ).scalar_one()
 
    matrix = db.execute(
        select(func.count()).where(
            ReportingRelationship.relationship_type == "MATRIX",
            ReportingRelationship.is_active == True,
        )
    ).scalar_one()
 
    # Individual contributors = employees who are not managers
    all_manager_ids = db.execute(
        select(ReportingRelationship.manager_id).where(
            ReportingRelationship.is_active == True
        ).distinct()
    ).scalars().all()
 
    total_employees = db.execute(select(func.count()).select_from(Employee)).scalar_one()
    individual_contributors = total_employees - len(set(all_manager_ids))
 
    return ReportingRelationshipSummary(
        direct_reports=direct,
        dotted_line_reports=dotted,
        matrix_reports=matrix,
        individual_contributors=max(individual_contributors, 0),
    )
 
 
@router.post("/reporting-relationships", response_model=ReportingRelationshipResponse, status_code=201)
def create_reporting_relationship(
    payload: ReportingRelationshipCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    obj = ReportingRelationship(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
 
 
@router.get("/reporting-relationships", response_model=List[ReportingRelationshipResponse])
def list_reporting_relationships(
    employee_id: Optional[int] = Query(None),
    relationship_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ReportingRelationship).where(ReportingRelationship.is_active == True)
    if employee_id:
        stmt = stmt.where(ReportingRelationship.employee_id == employee_id)
    if relationship_type:
        stmt = stmt.where(ReportingRelationship.relationship_type == relationship_type)
    return db.execute(stmt).scalars().all()
 
 
@router.put("/reporting-relationships/{relationship_id}", response_model=ReportingRelationshipResponse)
def update_reporting_relationship(
    relationship_id: int,
    payload: ReportingRelationshipUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    obj = db.get(ReportingRelationship, relationship_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reporting relationship not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj
 
 
@router.delete("/reporting-relationships/{relationship_id}", status_code=204)
def delete_reporting_relationship(
    relationship_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    obj = db.get(ReportingRelationship, relationship_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Reporting relationship not found.")
    obj.is_active = False
    db.commit()
 
 
@router.get("/hierarchy-health", response_model=HierarchyHealth)
def get_hierarchy_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    total_employees = db.execute(select(func.count()).select_from(Employee)).scalar_one()
 
    employees_with_manager = db.execute(
        select(func.count()).select_from(ReportingRelationship).where(
            ReportingRelationship.relationship_type == "DIRECT",
            ReportingRelationship.is_active == True,
        )
    ).scalar_one()
 
    reporting_completeness = (
        round((employees_with_manager / total_employees) * 100, 1)
        if total_employees > 0 else 0.0
    )
 
    # Span of control: overloaded > 10 reports, underloaded < 2 reports
    manager_spans = db.execute(
        select(ReportingRelationship.manager_id, func.count().label("cnt"))
        .where(
            ReportingRelationship.relationship_type == "DIRECT",
            ReportingRelationship.is_active == True,
        )
        .group_by(ReportingRelationship.manager_id)
    ).all()
 
    overloaded = sum(1 for r in manager_spans if r.cnt > 10)
    underloaded = sum(1 for r in manager_spans if r.cnt < 2)
 
    num_managers = len(manager_spans)
    num_ics = total_employees - num_managers
    ratio = f"{round(num_ics / num_managers)}:1" if num_managers > 0 else "N/A"
 
    return HierarchyHealth(
        reporting_completeness_pct=reporting_completeness,
        overloaded_managers=overloaded,
        underloaded_managers=underloaded,
        manager_to_ic_ratio=ratio,
    )
 
@router.get("/span-of-control", response_model=SpanOfControlAnalytics)
def get_span_of_control(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Span of Control Analytics — Management Insights section."""
    manager_spans = db.execute(
        select(ReportingRelationship.manager_id, func.count().label("cnt"))
        .where(
            ReportingRelationship.relationship_type == "DIRECT",
            ReportingRelationship.is_active == True,
        )
        .group_by(ReportingRelationship.manager_id)
    ).all()
 
    if not manager_spans:
        return SpanOfControlAnalytics(
            average_span=0.0,
            overloaded_count=0,
            underloaded_count=0,
            details=[],
        )
 
    avg = round(sum(r.cnt for r in manager_spans) / len(manager_spans), 1)
    overloaded = sum(1 for r in manager_spans if r.cnt > 10)
    underloaded = sum(1 for r in manager_spans if r.cnt < 2)
 
    details = []
    for r in manager_spans:
        emp = db.get(Employee, r.manager_id)
        name = f"{emp.first_name} {emp.last_name}" if emp else f"Employee #{r.manager_id}"
        if r.cnt > 10:
            status = "OVERLOADED"
        elif r.cnt < 2:
            status = "UNDERLOADED"
        else:
            status = "NORMAL"
        details.append(SpanOfControlItem(
            manager_id=r.manager_id,
            manager_name=name,
            direct_report_count=r.cnt,
            status=status,
        ))
 
    return SpanOfControlAnalytics(
        average_span=avg,
        overloaded_count=overloaded,
        underloaded_count=underloaded,
        details=details,
    )
 

@router.post("/change-requests", response_model=HierarchyChangeRequestResponse, status_code=201)
def create_change_request(
    payload: HierarchyChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Raise a hierarchy modification request (department change, manager change, etc.)."""
    obj = HierarchyChangeRequest(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
 
 
@router.get("/change-requests", response_model=List[HierarchyChangeRequestResponse])
def list_change_requests(
    status: Optional[str] = Query(None, description="PENDING | APPROVED | REJECTED"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(HierarchyChangeRequest)
    if status:
        stmt = stmt.where(HierarchyChangeRequest.status == status)
    return db.execute(stmt).scalars().all()
 
 
@router.patch("/change-requests/{request_id}", response_model=HierarchyChangeRequestResponse)
def action_change_request(
    request_id: int,
    payload: HierarchyChangeRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["superadmin", "admin", "hr_admin"])),
):
    """Approve or reject a hierarchy change request."""
    obj = db.get(HierarchyChangeRequest, request_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Change request not found.")
    obj.status = payload.status
    if payload.remarks:
        obj.remarks = payload.remarks
    if payload.approved_by:
        obj.approved_by = payload.approved_by
    db.commit()
    db.refresh(obj)
    return obj
 

@router.get("/history/{employee_id}", response_model=List[HierarchyHistoryResponse])
def get_employee_hierarchy_history(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full hierarchy history for an employee — time-travel view."""
    records = db.execute(
        select(HierarchyHistory)
        .where(HierarchyHistory.employee_id == employee_id)
        .order_by(HierarchyHistory.effective_from.desc())
    ).scalars().all()
    return records
 
 
@router.get("/history", response_model=List[HierarchyHistoryResponse])
def list_hierarchy_history(
    department_id: Optional[int] = Query(None),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all hierarchy history records with optional filters."""
    stmt = select(HierarchyHistory)
    if department_id:
        stmt = stmt.where(HierarchyHistory.department_id == department_id)
    if from_date:
        stmt = stmt.where(HierarchyHistory.effective_from >= datetime.strptime(from_date, "%Y-%m-%d"))
    if to_date:
        stmt = stmt.where(HierarchyHistory.effective_from <= datetime.strptime(to_date, "%Y-%m-%d"))
    stmt = stmt.order_by(HierarchyHistory.effective_from.desc())
    return db.execute(stmt).scalars().all()
 

@router.get("/department-location-view", response_model=List[DepartmentLocationView])
def get_department_location_view(
    location: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Department & Location Views — filtered view of departments with employee counts."""
    stmt = select(Department).where(Department.is_active == True)
    if location:
        stmt = stmt.where(Department.location.ilike(f"%{location}%"))
    departments = db.execute(stmt).scalars().all()
 
    result = []
    for dept in departments:
        emp_count = db.execute(
            select(func.count()).select_from(EmployeeMaster)
            .join(Employee, EmployeeMaster.employee_id == Employee.id)
            .where(EmployeeMaster.work_location == dept.location)
        ).scalar_one()
 
        result.append(DepartmentLocationView(
            department_id=dept.id,
            department_name=dept.name,
            location=dept.location,
            employee_count=emp_count,
            head_employee_id=dept.head_employee_id,
        ))
 
    return result