from __future__ import annotations

from datetime import date, timedelta, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import Session, relationship

from core.database import Base, get_db
from core.dependencies import get_current_user
from model.models import User
from model.HR_Automation.shift import Shift
from model.HR_Automation.work_hour_rule import WorkHourRule
from model.onboarding.employee import Employee

from schema.HR_Automation.shift import (
    
    ShiftCreate, ShiftUpdate, ShiftResponse,
    
    ShiftAssignmentCreate, BulkShiftAssignmentCreate,
    ShiftAssignmentResponse, ShiftAssignmentUpdate,
    
    RosterCreate, RosterResponse, RosterUpdate,
    
    ShiftSwapCreate, ShiftSwapResponse, ShiftSwapUpdate,
    
    FlexibleArrangementCreate, FlexibleArrangementResponse, FlexibleArrangementUpdate,
    
    WorkHourRulesConfig, AttendanceRulesSchema, OvertimeRulesSchema, BreakManagementSchema,
    
    NotificationOut,
)

router = APIRouter(prefix="/shifts", tags=["Shift Management"])




class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"
    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    shift_id    = Column(Integer, ForeignKey("shifts.id"),    nullable=False)
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=True)
    status      = Column(String(20), default="active")   
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ShiftRoster(Base):
    __tablename__ = "shift_rosters"
    id          = Column(Integer, primary_key=True, index=True)
    roster_name = Column(String(200), nullable=False)
    shift_id    = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    period      = Column(String(20), nullable=False)    
    start_date  = Column(Date, nullable=False)
    end_date    = Column(Date, nullable=False)
    status      = Column(String(20), default="draft")    
    published   = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"
    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False)
    current_shift_id    = Column(Integer, ForeignKey("shifts.id"),    nullable=False)
    requested_shift_id  = Column(Integer, ForeignKey("shifts.id"),    nullable=False)
    swap_date           = Column(Date, nullable=False)
    reason              = Column(Text, nullable=True)
    status              = Column(String(20), default="pending")   
    remarks             = Column(Text, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FlexibleArrangement(Base):
    __tablename__ = "flexible_arrangements"
    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(Integer, ForeignKey("employees.id"), nullable=False)
    arrangement_type = Column(String(50), nullable=False)   
    core_hours       = Column(String(50), nullable=False)   
    flexible_window  = Column(String(50), nullable=False)  
    remote_days      = Column(String(200), nullable=False)  
    status           = Column(String(20), default="active")
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkHourConfig(Base):
    
    __tablename__ = "work_hour_configs"
    id                                   = Column(Integer, primary_key=True, index=True)
    
    late_arrival_grace_period            = Column(Integer, default=15)
    minimum_work_hours                   = Column(Integer, default=8)
    half_day_threshold                   = Column(Float,   default=4.0)
    weekend_working_requires_approval    = Column(Boolean, default=True)
    holiday_working_requires_approval    = Column(Boolean, default=True)
    
    weekday_overtime_rate                = Column(Float, default=1.5)
    weekend_overtime_rate                = Column(Float, default=2.0)
    holiday_overtime_rate                = Column(Float, default=3.0)
    daily_overtime_cap                   = Column(Float, default=4.0)
    weekly_overtime_cap                  = Column(Float, default=20.0)
    
    allow_multiple_breaks                = Column(Boolean, default=True)
    break_punch_required                 = Column(Boolean, default=False)
    max_break_duration                   = Column(Integer, default=120)
    unpaid_break_threshold               = Column(Integer, default=30)
    updated_at                           = Column(DateTime, default=datetime.utcnow,
                                                  onupdate=datetime.utcnow)



try:
    Base.metadata.create_all(bind=Base.metadata.bind or __import__("core.database", fromlist=["engine"]).engine)
except Exception:
    pass   



def _emp_name(emp: Employee) -> str:
    return f"{emp.first_name} {emp.last_name or ''}".strip()


def _get_emp(db: Session, employee_id: int) -> Employee:
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


def _get_shift(db: Session, shift_id: int) -> Shift:
    shift = db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    return shift


def _roster_end_date(start: date, period: str) -> date:
    if period == "Weekly":
        return start + timedelta(days=6)
    elif period == "Biweekly":
        return start + timedelta(days=13)
    else:  # Monthly
        import calendar
        last = calendar.monthrange(start.year, start.month)[1]
        return start.replace(day=last)




@router.get("/", response_model=List[ShiftResponse])
def list_shifts(
    search:     Optional[str] = Query(None, description="Search by name or code"),
    shift_type: Optional[str] = Query(None, description="general|night|rotational|flexible"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Shift)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Shift.shift_name.ilike(like)) | (Shift.shift_code.ilike(like))
        )
    if shift_type and shift_type != "All Types":
        q = q.filter(Shift.shift_type == shift_type)
    return q.order_by(Shift.shift_name).all()


@router.post("/", response_model=ShiftResponse, status_code=201)
def create_shift(
    payload: ShiftCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    if db.query(Shift).filter(Shift.shift_name == payload.shift_name).first():
        raise HTTPException(status_code=400, detail="Shift name already exists")
    if db.query(Shift).filter(Shift.shift_code == payload.shift_code).first():
        raise HTTPException(status_code=400, detail="Shift code already exists")
    shift = Shift(**payload.model_dump())
    db.add(shift)
    db.commit()
    db.refresh(shift)
    return shift


@router.get("/{shift_id}", response_model=ShiftResponse)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_shift(db, shift_id)


@router.patch("/{shift_id}", response_model=ShiftResponse)
def update_shift(
    shift_id: int,
    payload: ShiftUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shift = _get_shift(db, shift_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(shift, key, value)
    db.commit()
    db.refresh(shift)
    return shift


@router.delete("/{shift_id}", status_code=200)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    shift = _get_shift(db, shift_id)
    db.delete(shift)
    db.commit()
    return {"message": "Shift deleted successfully"}




@router.post("/assignments/individual", response_model=ShiftAssignmentResponse, status_code=201)
def individual_shift_assignment(
    payload: ShiftAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp   = _get_emp(db, payload.employee_id)
    shift = _get_shift(db, payload.shift_id)

    
    existing = db.query(ShiftAssignment).filter(
        ShiftAssignment.employee_id == payload.employee_id,
        ShiftAssignment.status == "active",
    ).first()
    if existing:
        existing.status = "inactive"

    assignment = ShiftAssignment(
        employee_id=payload.employee_id,
        shift_id=payload.shift_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="active" if payload.start_date <= date.today() else "upcoming",
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return ShiftAssignmentResponse(
        id=assignment.id,
        employee_id=emp.id,
        employee_name=_emp_name(emp),
        employee_code=emp.employee_code,
        shift_id=shift.id,
        shift_name=shift.shift_name,
        shift_code=shift.shift_code,
        start_date=assignment.start_date,
        end_date=assignment.end_date,
        status=assignment.status,
    )


@router.post("/assignments/bulk", status_code=201)
def bulk_shift_assignment(
    payload: BulkShiftAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shift   = _get_shift(db, payload.shift_id)
    results = []
    errors  = []

    for emp_id in payload.employee_ids:
        emp = db.get(Employee, emp_id)
        if not emp:
            errors.append({"employee_id": emp_id, "error": "Not found"})
            continue

        
        existing = db.query(ShiftAssignment).filter(
            ShiftAssignment.employee_id == emp_id,
            ShiftAssignment.status == "active",
        ).first()
        if existing:
            existing.status = "inactive"

        assignment = ShiftAssignment(
            employee_id=emp_id,
            shift_id=payload.shift_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status="active" if payload.start_date <= date.today() else "upcoming",
        )
        db.add(assignment)
        results.append(emp.employee_code)

    db.commit()
    return {
        "message": f"{len(results)} employees assigned to {shift.shift_name}",
        "assigned": results,
        "errors": errors,
    }


@router.get("/assignments", response_model=List[ShiftAssignmentResponse])
def list_shift_assignments(
    status:     Optional[str] = Query(None, description="active|inactive|upcoming"),
    shift_id:   Optional[int] = Query(None),
    search:     Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ShiftAssignment)
    if status:
        q = q.filter(ShiftAssignment.status == status)
    if shift_id:
        q = q.filter(ShiftAssignment.shift_id == shift_id)

    assignments = q.order_by(ShiftAssignment.start_date.desc()).all()
    result = []
    for a in assignments:
        emp   = db.get(Employee, a.employee_id)
        shift = db.get(Shift, a.shift_id)
        if not emp or not shift:
            continue
        if search:
            name = _emp_name(emp).lower()
            if search.lower() not in name and search.lower() not in emp.employee_code.lower():
                continue
        result.append(ShiftAssignmentResponse(
            id=a.id,
            employee_id=emp.id,
            employee_name=_emp_name(emp),
            employee_code=emp.employee_code,
            shift_id=shift.id,
            shift_name=shift.shift_name,
            shift_code=shift.shift_code,
            start_date=a.start_date,
            end_date=a.end_date,
            status=a.status,
        ))
    return result


@router.patch("/assignments/{assignment_id}", response_model=ShiftAssignmentResponse)
def update_shift_assignment(
    assignment_id: int,
    payload: ShiftAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    a = db.get(ShiftAssignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(a, key, value)
    db.commit()
    db.refresh(a)
    emp   = db.get(Employee, a.employee_id)
    shift = db.get(Shift, a.shift_id)
    return ShiftAssignmentResponse(
        id=a.id,
        employee_id=emp.id,
        employee_name=_emp_name(emp),
        employee_code=emp.employee_code,
        shift_id=shift.id,
        shift_name=shift.shift_name,
        shift_code=shift.shift_code,
        start_date=a.start_date,
        end_date=a.end_date,
        status=a.status,
    )


@router.delete("/assignments/{assignment_id}", status_code=200)
def delete_shift_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    a = db.get(ShiftAssignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(a)
    db.commit()
    return {"message": "Assignment removed"}




@router.post("/rosters", response_model=RosterResponse, status_code=201)
def generate_roster(
    payload: RosterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shift    = _get_shift(db, payload.shift_id)
    end_date = _roster_end_date(payload.start_date, payload.period)

    roster_name = f"{shift.shift_name} - {payload.period} ({payload.start_date})"

    roster = ShiftRoster(
        roster_name=roster_name,
        shift_id=payload.shift_id,
        period=payload.period,
        start_date=payload.start_date,
        end_date=end_date,
        status="draft",
        published=False,
    )
    db.add(roster)
    db.commit()
    db.refresh(roster)

    return RosterResponse(
        id=roster.id,
        roster_name=roster.roster_name,
        shift_id=shift.id,
        shift_name=shift.shift_name,
        period=roster.period,
        start_date=roster.start_date,
        end_date=roster.end_date,
        status=roster.status,
        published=roster.published,
        created_at=roster.created_at,
    )


@router.get("/rosters", response_model=List[RosterResponse])
def list_rosters(
    status:   Optional[str] = Query(None, description="draft|published|archived"),
    shift_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ShiftRoster)
    if status:
        q = q.filter(ShiftRoster.status == status)
    if shift_id:
        q = q.filter(ShiftRoster.shift_id == shift_id)

    rosters = q.order_by(ShiftRoster.start_date.desc()).all()
    result  = []
    for r in rosters:
        shift = db.get(Shift, r.shift_id)
        result.append(RosterResponse(
            id=r.id,
            roster_name=r.roster_name,
            shift_id=r.shift_id,
            shift_name=shift.shift_name if shift else "Unknown",
            period=r.period,
            start_date=r.start_date,
            end_date=r.end_date,
            status=r.status,
            published=r.published,
            created_at=r.created_at,
        ))
    return result


@router.patch("/rosters/{roster_id}", response_model=RosterResponse)
def update_roster(
    roster_id: int,
    payload: RosterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
   
    roster = db.get(ShiftRoster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    if payload.status:
        roster.status = payload.status
    if payload.published is not None:
        roster.published = payload.published
        if payload.published:
            roster.status = "published"
    db.commit()
    db.refresh(roster)
    shift = db.get(Shift, roster.shift_id)
    return RosterResponse(
        id=roster.id,
        roster_name=roster.roster_name,
        shift_id=roster.shift_id,
        shift_name=shift.shift_name if shift else "Unknown",
        period=roster.period,
        start_date=roster.start_date,
        end_date=roster.end_date,
        status=roster.status,
        published=roster.published,
        created_at=roster.created_at,
    )


@router.delete("/rosters/{roster_id}", status_code=200)
def delete_roster(
    roster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roster = db.get(ShiftRoster, roster_id)
    if not roster:
        raise HTTPException(status_code=404, detail="Roster not found")
    db.delete(roster)
    db.commit()
    return {"message": "Roster deleted"}




@router.post("/swaps", response_model=ShiftSwapResponse, status_code=201)
def create_swap_request(
    payload: ShiftSwapCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp      = _get_emp(db, payload.employee_id)
    cur_shift = _get_shift(db, payload.current_shift_id)
    req_shift = _get_shift(db, payload.requested_shift_id)

    swap = ShiftSwapRequest(
        employee_id=payload.employee_id,
        current_shift_id=payload.current_shift_id,
        requested_shift_id=payload.requested_shift_id,
        swap_date=payload.swap_date,
        reason=payload.reason,
        status="pending",
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)

    return ShiftSwapResponse(
        id=swap.id,
        employee_id=emp.id,
        employee_name=_emp_name(emp),
        current_shift=cur_shift.shift_name,
        requested_shift=req_shift.shift_name,
        swap_date=swap.swap_date,
        reason=swap.reason,
        status=swap.status,
        created_at=swap.created_at,
    )


@router.get("/swaps", response_model=List[ShiftSwapResponse])
def list_swap_requests(
    status: Optional[str] = Query(None, description="pending|approved|rejected"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(ShiftSwapRequest)
    if status:
        q = q.filter(ShiftSwapRequest.status == status)
    swaps  = q.order_by(ShiftSwapRequest.created_at.desc()).all()
    result = []
    for s in swaps:
        emp       = db.get(Employee, s.employee_id)
        cur_shift = db.get(Shift, s.current_shift_id)
        req_shift = db.get(Shift, s.requested_shift_id)
        result.append(ShiftSwapResponse(
            id=s.id,
            employee_id=s.employee_id,
            employee_name=_emp_name(emp) if emp else "Unknown",
            current_shift=cur_shift.shift_name if cur_shift else "Unknown",
            requested_shift=req_shift.shift_name if req_shift else "Unknown",
            swap_date=s.swap_date,
            reason=s.reason,
            status=s.status,
            created_at=s.created_at,
        ))
    return result


@router.patch("/swaps/{swap_id}", response_model=ShiftSwapResponse)
def update_swap_request(
    swap_id: int,
    payload: ShiftSwapUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    swap = db.get(ShiftSwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")

    swap.status  = payload.status
    swap.remarks = payload.remarks

    
    if payload.status == "approved":
        assignment = db.query(ShiftAssignment).filter(
            ShiftAssignment.employee_id == swap.employee_id,
            ShiftAssignment.status == "active",
        ).first()
        if assignment:
            assignment.shift_id = swap.requested_shift_id

    db.commit()
    db.refresh(swap)
    emp       = db.get(Employee, swap.employee_id)
    cur_shift = db.get(Shift, swap.current_shift_id)
    req_shift = db.get(Shift, swap.requested_shift_id)
    return ShiftSwapResponse(
        id=swap.id,
        employee_id=swap.employee_id,
        employee_name=_emp_name(emp) if emp else "Unknown",
        current_shift=cur_shift.shift_name if cur_shift else "Unknown",
        requested_shift=req_shift.shift_name if req_shift else "Unknown",
        swap_date=swap.swap_date,
        reason=swap.reason,
        status=swap.status,
        created_at=swap.created_at,
    )


@router.delete("/swaps/{swap_id}", status_code=200)
def delete_swap_request(
    swap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    swap = db.get(ShiftSwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")
    db.delete(swap)
    db.commit()
    return {"message": "Swap request deleted"}




@router.post("/flexible", response_model=FlexibleArrangementResponse, status_code=201)
def create_flexible_arrangement(
    payload: FlexibleArrangementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = _get_emp(db, payload.employee_id)
    arr = FlexibleArrangement(**payload.model_dump())
    db.add(arr)
    db.commit()
    db.refresh(arr)
    return FlexibleArrangementResponse(
        id=arr.id,
        employee_id=emp.id,
        employee_name=_emp_name(emp),
        arrangement_type=arr.arrangement_type,
        core_hours=arr.core_hours,
        flexible_window=arr.flexible_window,
        remote_days=arr.remote_days,
        status=arr.status,
        created_at=arr.created_at,
    )


@router.get("/flexible", response_model=List[FlexibleArrangementResponse])
def list_flexible_arrangements(
    status:      Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(FlexibleArrangement)
    if status:
        q = q.filter(FlexibleArrangement.status == status)
    if employee_id:
        q = q.filter(FlexibleArrangement.employee_id == employee_id)
    arrangements = q.order_by(FlexibleArrangement.created_at.desc()).all()
    result = []
    for a in arrangements:
        emp = db.get(Employee, a.employee_id)
        result.append(FlexibleArrangementResponse(
            id=a.id,
            employee_id=a.employee_id,
            employee_name=_emp_name(emp) if emp else "Unknown",
            arrangement_type=a.arrangement_type,
            core_hours=a.core_hours,
            flexible_window=a.flexible_window,
            remote_days=a.remote_days,
            status=a.status,
            created_at=a.created_at,
        ))
    return result


@router.patch("/flexible/{arrangement_id}", response_model=FlexibleArrangementResponse)
def update_flexible_arrangement(
    arrangement_id: int,
    payload: FlexibleArrangementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    arr = db.get(FlexibleArrangement, arrangement_id)
    if not arr:
        raise HTTPException(status_code=404, detail="Arrangement not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(arr, key, value)
    db.commit()
    db.refresh(arr)
    emp = db.get(Employee, arr.employee_id)
    return FlexibleArrangementResponse(
        id=arr.id,
        employee_id=arr.employee_id,
        employee_name=_emp_name(emp) if emp else "Unknown",
        arrangement_type=arr.arrangement_type,
        core_hours=arr.core_hours,
        flexible_window=arr.flexible_window,
        remote_days=arr.remote_days,
        status=arr.status,
        created_at=arr.created_at,
    )


@router.delete("/flexible/{arrangement_id}", status_code=200)
def delete_flexible_arrangement(
    arrangement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    arr = db.get(FlexibleArrangement, arrangement_id)
    if not arr:
        raise HTTPException(status_code=404, detail="Arrangement not found")
    db.delete(arr)
    db.commit()
    return {"message": "Arrangement deleted"}




def _config_to_schema(cfg: WorkHourConfig) -> WorkHourRulesConfig:
    return WorkHourRulesConfig(
        attendance=AttendanceRulesSchema(
            late_arrival_grace_period=cfg.late_arrival_grace_period,
            minimum_work_hours=cfg.minimum_work_hours,
            half_day_threshold=cfg.half_day_threshold,
            weekend_working_requires_approval=cfg.weekend_working_requires_approval,
            holiday_working_requires_approval=cfg.holiday_working_requires_approval,
        ),
        overtime=OvertimeRulesSchema(
            weekday_overtime_rate=cfg.weekday_overtime_rate,
            weekend_overtime_rate=cfg.weekend_overtime_rate,
            holiday_overtime_rate=cfg.holiday_overtime_rate,
            daily_overtime_cap=cfg.daily_overtime_cap,
            weekly_overtime_cap=cfg.weekly_overtime_cap,
        ),
        breaks=BreakManagementSchema(
            allow_multiple_breaks=cfg.allow_multiple_breaks,
            break_punch_required=cfg.break_punch_required,
            max_break_duration=cfg.max_break_duration,
            unpaid_break_threshold=cfg.unpaid_break_threshold,
        ),
    )


@router.get("/work-hour-rules", response_model=WorkHourRulesConfig)
def get_work_hour_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = db.query(WorkHourConfig).first()
    if not cfg:
        
        return WorkHourRulesConfig()
    return _config_to_schema(cfg)


@router.put("/work-hour-rules", response_model=WorkHourRulesConfig)
def save_work_hour_rules(
    payload: WorkHourRulesConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cfg = db.query(WorkHourConfig).first()
    if not cfg:
        cfg = WorkHourConfig()
        db.add(cfg)

    
    cfg.late_arrival_grace_period         = payload.attendance.late_arrival_grace_period
    cfg.minimum_work_hours                = payload.attendance.minimum_work_hours
    cfg.half_day_threshold                = payload.attendance.half_day_threshold
    cfg.weekend_working_requires_approval = payload.attendance.weekend_working_requires_approval
    cfg.holiday_working_requires_approval = payload.attendance.holiday_working_requires_approval
    
    cfg.weekday_overtime_rate             = payload.overtime.weekday_overtime_rate
    cfg.weekend_overtime_rate             = payload.overtime.weekend_overtime_rate
    cfg.holiday_overtime_rate             = payload.overtime.holiday_overtime_rate
    cfg.daily_overtime_cap                = payload.overtime.daily_overtime_cap
    cfg.weekly_overtime_cap               = payload.overtime.weekly_overtime_cap
    
    cfg.allow_multiple_breaks             = payload.breaks.allow_multiple_breaks
    cfg.break_punch_required              = payload.breaks.break_punch_required
    cfg.max_break_duration                = payload.breaks.max_break_duration
    cfg.unpaid_break_threshold            = payload.breaks.unpaid_break_threshold

    db.commit()
    db.refresh(cfg)
    return _config_to_schema(cfg)




@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = []
    nid = 1

   
    pending_swaps = db.query(ShiftSwapRequest).filter(
        ShiftSwapRequest.status == "pending"
    ).order_by(ShiftSwapRequest.created_at.desc()).limit(10).all()

    for s in pending_swaps:
        emp = db.get(Employee, s.employee_id)
        notifications.append(NotificationOut(
            id=nid,
            message=f"{_emp_name(emp) if emp else 'Employee'} requested shift swap on {s.swap_date}",
            type="swap_request",
            is_read=False,
            created_at=s.created_at,
        ))
        nid += 1

   
    published = db.query(ShiftRoster).filter(
        ShiftRoster.published == True
    ).order_by(ShiftRoster.start_date.desc()).limit(5).all()

    for r in published:
        notifications.append(NotificationOut(
            id=nid,
            message=f"Roster '{r.roster_name}' has been published",
            type="roster_published",
            is_read=False,
            created_at=r.created_at,
        ))
        nid += 1

    return notifications



@router.get("/employees-list")
def employees_for_assignment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employees = db.query(Employee).filter(Employee.is_active == True).order_by(Employee.first_name).all()
    return [
        {
            "id": e.id,
            "name": _emp_name(e),
            "code": e.employee_code,
            "department": e.department or "",
        }
        for e in employees
    ]


