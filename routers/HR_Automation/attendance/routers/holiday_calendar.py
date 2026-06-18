
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from core.database import get_db
from schema.HR_Automation.holiday import (
    OptionalHolidayApplicationCreate, OptionalHolidayApplicationUpdate, OptionalHolidayApplicationOut,
    OptionalAppStatus,
    HolidayCalendarCreate, HolidayCalendarUpdate, HolidayCalendarOut, CalendarHolidayLink,
    HolidaySwapRequestCreate, HolidaySwapRequestUpdate, HolidaySwapRequestOut,
    SwapRequestStatus,
    HolidayCarryForwardOut, ProcessCarryForwardRequest,
    HolidayCalendarTabSummary,
)
import services.HR_Automation.holiday_service as svc

router = APIRouter(
    prefix="/holiday-calendar",
    tags=["Holiday Calendar"],
)



@router.get("/tab-summary", response_model=HolidayCalendarTabSummary)
def get_tab_summary(db: Session = Depends(get_db)):
    
    return svc.get_tab_summary(db)




@router.post("/optional-apps", response_model=OptionalHolidayApplicationOut, status_code=201)
def apply_optional_holiday(payload: OptionalHolidayApplicationCreate, db: Session = Depends(get_db)):
   
    try:
        return svc.apply_optional_holiday(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/optional-apps", response_model=List[OptionalHolidayApplicationOut])
def list_optional_apps(
    employee_id: Optional[int] = Query(None),
    status: Optional[OptionalAppStatus] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_optional_applications(db, employee_id=employee_id, status=status)


@router.patch("/optional-apps/{application_id}", response_model=OptionalHolidayApplicationOut)
def update_optional_app(
    application_id: int, payload: OptionalHolidayApplicationUpdate, db: Session = Depends(get_db)
):
    
    try:
        return svc.update_optional_application(db, application_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/optional-apps/{application_id}")
def delete_optional_app(application_id: int, db: Session = Depends(get_db)):
    if not svc.delete_optional_application(db, application_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return {"message": "Application deleted"}




@router.post("/calendars", response_model=HolidayCalendarOut, status_code=201)
def add_calendar(payload: HolidayCalendarCreate, db: Session = Depends(get_db)):
    
    calendar = svc.add_calendar(db, payload)
    return {
        "id": calendar.id,
        "calendar_name": calendar.calendar_name,
        "location": calendar.location,
        "employee_groups": calendar.employee_groups,
        "status": calendar.status,
        "is_default": calendar.is_default,
        "description": calendar.description,
        "holiday_count": len(payload.holiday_ids or []),
        "created_at": calendar.created_at,
    }


@router.get("/calendars", response_model=List[HolidayCalendarOut])
def list_calendars(db: Session = Depends(get_db)):
    
    return svc.list_calendars(db)


@router.patch("/calendars/{calendar_id}", response_model=HolidayCalendarOut)
def update_calendar(calendar_id: int, payload: HolidayCalendarUpdate, db: Session = Depends(get_db)):
    
    try:
        calendar = svc.update_calendar(db, calendar_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    holiday_count = len(svc.get_calendar_holidays(db, calendar_id))
    return {
        "id": calendar.id,
        "calendar_name": calendar.calendar_name,
        "location": calendar.location,
        "employee_groups": calendar.employee_groups,
        "status": calendar.status,
        "is_default": calendar.is_default,
        "description": calendar.description,
        "holiday_count": holiday_count,
        "created_at": calendar.created_at,
    }


@router.delete("/calendars/{calendar_id}")
def delete_calendar(calendar_id: int, db: Session = Depends(get_db)):
    
    if not svc.delete_calendar(db, calendar_id):
        raise HTTPException(status_code=404, detail="Calendar not found")
    return {"message": "Calendar deleted"}


@router.post("/calendars/link-holiday")
def link_holiday(payload: CalendarHolidayLink, db: Session = Depends(get_db)):
    
    mapping = svc.link_holiday_to_calendar(db, payload)
    return {"message": "Holiday linked to calendar", "mapping_id": mapping.id}


@router.delete("/calendars/{calendar_id}/holidays/{holiday_id}")
def unlink_holiday(calendar_id: int, holiday_id: int, db: Session = Depends(get_db)):
   
    if not svc.unlink_holiday_from_calendar(db, calendar_id, holiday_id):
        raise HTTPException(status_code=404, detail="Link not found")
    return {"message": "Holiday unlinked from calendar"}


@router.get("/calendars/{calendar_id}/holidays")
def get_calendar_holidays(calendar_id: int, db: Session = Depends(get_db)):
    
    return svc.get_calendar_holidays(db, calendar_id)




@router.post("/swap-requests", response_model=HolidaySwapRequestOut, status_code=201)
def create_swap_request(payload: HolidaySwapRequestCreate, db: Session = Depends(get_db)):
   
    try:
        swap = svc.create_swap_request(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "id": swap.id,
        "employee_id": swap.employee_id,
        "employee_name": None,
        "holiday_id": swap.holiday_id,
        "holiday_date": swap.holiday_date,
        "work_date": swap.work_date,
        "reason": swap.reason,
        "status": swap.status,
        "approved_by": swap.approved_by,
        "approved_on": swap.approved_on,
        "rejection_reason": swap.rejection_reason,
        "created_at": swap.created_at,
    }


@router.get("/swap-requests", response_model=List[HolidaySwapRequestOut])
def list_swap_requests(
    employee_id: Optional[int] = Query(None),
    status: Optional[SwapRequestStatus] = Query(None),
    db: Session = Depends(get_db),
):
   
    return svc.list_swap_requests(db, employee_id=employee_id, status=status)


@router.patch("/swap-requests/{swap_id}", response_model=HolidaySwapRequestOut)
def update_swap_request(swap_id: int, payload: HolidaySwapRequestUpdate, db: Session = Depends(get_db)):
    
    try:
        swap = svc.update_swap_request(db, swap_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "id": swap.id,
        "employee_id": swap.employee_id,
        "employee_name": None,
        "holiday_id": swap.holiday_id,
        "holiday_date": swap.holiday_date,
        "work_date": swap.work_date,
        "reason": swap.reason,
        "status": swap.status,
        "approved_by": swap.approved_by,
        "approved_on": swap.approved_on,
        "rejection_reason": swap.rejection_reason,
        "created_at": swap.created_at,
    }


@router.post("/swap-requests/{swap_id}/cancel", response_model=HolidaySwapRequestOut)
def cancel_swap_request(swap_id: int, db: Session = Depends(get_db)):
    try:
        swap = svc.cancel_swap_request(db, swap_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "id": swap.id,
        "employee_id": swap.employee_id,
        "employee_name": None,
        "holiday_id": swap.holiday_id,
        "holiday_date": swap.holiday_date,
        "work_date": swap.work_date,
        "reason": swap.reason,
        "status": swap.status,
        "approved_by": swap.approved_by,
        "approved_on": swap.approved_on,
        "rejection_reason": swap.rejection_reason,
        "created_at": swap.created_at,
    }




@router.post("/carry-forward/process", response_model=List[HolidayCarryForwardOut])
def process_carry_forward(payload: ProcessCarryForwardRequest, db: Session = Depends(get_db)):
    
    try:
        records = svc.process_carry_forward(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return svc.list_carry_forward_records(
        db,
        from_year=payload.from_year,
        to_year=payload.to_year,
    )


@router.get("/carry-forward", response_model=List[HolidayCarryForwardOut])
def list_carry_forward(
    employee_id: Optional[int] = Query(None),
    from_year: Optional[int] = Query(None),
    to_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    
    return svc.list_carry_forward_records(db, employee_id=employee_id, from_year=from_year, to_year=to_year)




@router.get("/quick-actions/today")
def quick_action_today(db: Session = Depends(get_db)):
   
    today = date.today()
    from model.HR_Automation.holiday import Holiday
    holiday_today = db.query(Holiday).filter(Holiday.holiday_date == today, Holiday.is_active == True).first()
    return {
        "date": today,
        "is_holiday": holiday_today is not None,
        "holiday_name": holiday_today.holiday_name if holiday_today else None,
    }


@router.get("/quick-actions/context")
def quick_action_context(active_tab: str = Query(..., description="One of: master, optional, calendars, swap, carry_forward")):
   
    mapping = {
        "master":         {"add": "POST /api/attendance/holidays", "apply": None},
        "optional":        {"add": None, "apply": "POST /api/attendance/holiday-calendar/optional-apps"},
        "calendars":       {"add": "POST /api/attendance/holiday-calendar/calendars", "apply": None},
        "swap":            {"add": "POST /api/attendance/holiday-calendar/swap-requests", "apply": None},
        "carry_forward":   {"add": "POST /api/attendance/holiday-calendar/carry-forward/process", "apply": None},
    }
    if active_tab not in mapping:
        raise HTTPException(status_code=400, detail="Invalid tab name")
    return mapping[active_tab]