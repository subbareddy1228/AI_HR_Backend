"""
routers/holiday_calendar.py
FastAPI router — Holiday Calendar module (all 5 tabs).
Prefix : /api/attendance/holidays
Auth   : JWT via get_current_user / require_hr_admin
"""

import io
from datetime import date
from typing import List, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, Path,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user

from model.HR_Automation.holiday_calendar import (
    ApplicationStatusEnum, SwapStatusEnum,
)
from schema.HR_Automation.holiday_calendar import (
    HolidayCreateIn, HolidayUpdateIn, HolidayOut, HolidayStats,
    ApplyOptionalIn, UpdateApplicationStatusIn, OptionalApplicationOut,
    HolidayCalendarCreateIn, HolidayCalendarUpdateIn, HolidayCalendarOut,
    SwapRequestIn, SwapDecisionIn, SwapRequestOut,
    CarryForwardIn, CarryForwardOut,
    CalendarMonthOut, FilterOptionsOut, MessageResponse,
)
from services.HR_Automation.holiday_calendar_service import (
    HolidayMasterService, OptionalApplicationService,
    HolidayCalendarService, HolidaySwapService,
    CarryForwardService, CalendarGridService,
    seed_holiday_defaults,
)

router = APIRouter(
    prefix="/api/attendance/holidays",
    tags=["Holiday Calendar"],
)


# ══════════════════════════════════════════════════════════
# CALENDAR GRID  (left panel — month mini-calendar)
# ══════════════════════════════════════════════════════════

@router.get("/calendar-grid", response_model=CalendarMonthOut)
def get_calendar_grid(
    year:        int     = Query(default_factory=lambda: date.today().year,
                                 ge=2000, le=2100),
    month:       int     = Query(default_factory=lambda: date.today().month,
                                 ge=1, le=12),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Left-panel month mini-calendar.
    ← / → arrow navigation to change month.
    Returns 6 weeks × 7 cols (Sun→Sat).
    Each day: isToday · isHoliday · holiday details (shown in red).
    """
    return CalendarGridService.get_month(db, year, month)


# ══════════════════════════════════════════════════════════
# TAB BADGE COUNTS  (shown on each tab: "3 Holidays", "0 Apps"…)
# ══════════════════════════════════════════════════════════

@router.get("/tab-counts")
def get_tab_counts(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Returns badge counts for all 5 tabs:
      Holiday Master  → N Holidays
      Optional Apps   → N Apps
      Calendars       → N Calendars
      Holiday Swap    → N Requests
      Carry Forward   → N Records
    """
    from models.holiday_calendar import (
        Holiday, OptionalHolidayApplication, HolidayCalendar,
        HolidaySwapRequest, HolidayCarryForward,
    )
    return {
        "holidayMaster":  db.query(Holiday).count(),
        "optionalApps":   db.query(OptionalHolidayApplication).count(),
        "calendars":      db.query(HolidayCalendar).count(),
        "holidaySwap":    db.query(HolidaySwapRequest).filter_by(status="pending").count(),
        "carryForward":   db.query(HolidayCarryForward).count(),
    }


# ══════════════════════════════════════════════════════════
# FILTER OPTIONS  (All Categories · All Types dropdowns)
# ══════════════════════════════════════════════════════════

@router.get("/filter-options", response_model=FilterOptionsOut)
def get_filter_options(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Populates:
      All Categories dropdown → distinct category values from holidays
      All Types dropdown      → gazetted | restricted | festival
      All Status              → Pending | Approved | Rejected
    """
    from sqlalchemy import distinct
    from model.HR_Automation.holiday_calendar import Holiday
    cats = sorted({
        v for (v,) in db.query(distinct(Holiday.category)).all() if v
    })
    return {
        "categories": ["All Categories"] + cats,
        "locations":  ["All"] + sorted({
            v for (v,) in db.query(distinct(Holiday.location)).all() if v
        }),
        "statuses":   ["All Status", "Pending", "Approved", "Rejected"],
    }


# ══════════════════════════════════════════════════════════
# TAB 1 — HOLIDAY MASTER
# ══════════════════════════════════════════════════════════

@router.get("/master", response_model=List[HolidayOut])
def list_holidays(
    search:      Optional[str] = Query(None, description="Search holiday name"),
    category:    Optional[str] = Query(None, description="All Categories | specific"),
    type_filter: Optional[str] = Query(None, alias="type",
                                        description="mandatory | optional"),
    year:        Optional[int] = Query(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Holiday Master tab — table.
    Columns: HOLIDAY NAME · DATE (red) · CATEGORY · HOLIDAY TYPE badge
             TYPE badge (Mandatory/Optional) · LOCATION · ACTIONS (✏ 🗑)
    Filters: Search box · All Categories dropdown · All Types dropdown
    """
    return HolidayMasterService.list(db, search, category, type_filter, year)


@router.get("/master/stats", response_model=HolidayStats)
def get_holiday_stats(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Stats shown across the 5 tab badges."""
    return HolidayMasterService.get_stats(db)


@router.post("/master", response_model=HolidayOut,
             status_code=status.HTTP_201_CREATED)
def create_holiday(
    payload:     HolidayCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Add Holiday button → Add Holiday modal → Save.
    Also triggered by Quick Actions → + Add button.
    Modal fields:
      Holiday Name* · Date* · Location · Category*
      Holiday Type (gazetted | restricted | festival)
      Optional toggle
        → Advance Booking Days
        → Allow Carry Forward + Carry Forward Limit
      Applicable Calendars · Applicable Employee Groups
    """
    return HolidayMasterService.create(db, payload, current_user.id)

@router.get("/master/export/csv")
def export_holidays(
    search:      Optional[str] = Query(None),
    category:    Optional[str] = Query(None),
    type_filter: Optional[str] = Query(None, alias="type"),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """Export button (green) → downloads Holiday Master as CSV."""
    csv_bytes = HolidayMasterService.export_csv(db, search, category, type_filter)
    return StreamingResponse(
        io.BytesIO(csv_bytes), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=holiday_master.csv"},
    )



@router.get("/master/{holiday_id}", response_model=HolidayOut)
def get_holiday(
    holiday_id:  int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """Returns one holiday — pre-populates the Edit modal."""
    try:
        return _build_out(HolidayMasterService.get(db, holiday_id))
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.put("/master/{holiday_id}", response_model=HolidayOut)
def update_holiday(
    holiday_id:  int            = Path(...),
    payload:     HolidayUpdateIn = ...,
    db:          Session        = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """✏ Edit icon → Edit Holiday modal → Save."""
    try:
        return HolidayMasterService.update(db, holiday_id, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.delete("/master/{holiday_id}", response_model=MessageResponse)
def delete_holiday(
    holiday_id:  int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """🗑 Trash icon — permanently deletes the holiday."""
    try:
        HolidayMasterService.delete(db, holiday_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": f"Holiday {holiday_id} deleted."}




# ══════════════════════════════════════════════════════════
# TAB 2 — OPTIONAL APPLICATIONS
# ══════════════════════════════════════════════════════════

@router.get("/optional-apps", response_model=List[OptionalApplicationOut])
def list_optional_applications(
    search:      Optional[str]                   = Query(None),
    status_filter:Optional[str]                  = Query(None, alias="status",
                                                          description="Pending|Approved|Rejected"),
    employee_id: Optional[str]                   = Query(None),
    db:          Session                         = Depends(get_db),
    current_user                                 = Depends(get_current_user),
):
    """
    Optional Apps tab — Optional Applications table.
    Columns: HOLIDAY · DATE · APPLIED ON · STATUS badge · REASON · ACTIONS (✏ 🗑)
    Filters: Search box · All Status dropdown
    """
    st = ApplicationStatusEnum(status_filter) if status_filter else None
    return OptionalApplicationService.list(db, search, st, employee_id)


@router.post("/optional-apps", response_model=OptionalApplicationOut,
             status_code=status.HTTP_201_CREATED)
def apply_optional_holiday(
    payload:     ApplyOptionalIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Apply Holiday button → Apply Optional Holiday modal → Apply.
    Also triggered by Quick Actions → ✓ Apply button.
    Modal fields:
      Select Holiday (dropdown — only optional=True holidays)
      Reason
    Validates advance booking days.
    Builds 2-level Manager → HR approval workflow.
    """
    try:
        return OptionalApplicationService.apply(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


@router.patch("/optional-apps/{app_id}/status",
              response_model=OptionalApplicationOut)
def update_application_status(
    app_id:      int                      = Path(...),
    payload:     UpdateApplicationStatusIn = ...,
    db:          Session                  = Depends(get_db),
    current_user                          = Depends(get_current_user),
):
    """
    ✏ Edit icon → Update Status modal → Save.
    Status options: Pending | Approved | Rejected
    """
    try:
        return OptionalApplicationService.update_status(
            db, app_id, payload.status,
            decided_by=getattr(current_user, "name", "HR Admin"),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.delete("/optional-apps/{app_id}", response_model=MessageResponse)
def delete_optional_application(
    app_id:      int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """🗑 Trash icon — deletes an optional holiday application."""
    try:
        OptionalApplicationService.delete(db, app_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    return {"message": f"Application {app_id} deleted."}


@router.get("/optional-apps/export/csv")
def export_optional_apps(
    status_filter: Optional[str] = Query(None, alias="status"),
    db:            Session       = Depends(get_db),
    current_user                 = Depends(get_current_user),
):
    """Export button → downloads Optional Applications as CSV."""
    st = ApplicationStatusEnum(status_filter) if status_filter else None
    csv_bytes = OptionalApplicationService.export_csv(db, st)
    return StreamingResponse(
        io.BytesIO(csv_bytes), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=optional_applications.csv"},
    )


# ══════════════════════════════════════════════════════════
# TAB 3 — CALENDARS
# ══════════════════════════════════════════════════════════

@router.get("/calendars", response_model=List[HolidayCalendarOut])
def list_calendars(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Calendars tab — Holiday Calendars table.
    Columns: Calendar Name · Location · Employee Groups · Status badge · Actions (✏ 🗑)
    Default calendar shown with "Default" badge.
    """
    return HolidayCalendarService.list(db)


@router.post("/calendars", response_model=HolidayCalendarOut,
             status_code=status.HTTP_201_CREATED)
def create_calendar(
    payload:     HolidayCalendarCreateIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Add Calendar button → Add Holiday Calendar modal → Save.
    Modal fields: Calendar Name* · Location* · Employee Group · Set as Default toggle
    If isDefault=True, unsets all other calendars' default flag.
    """
    return HolidayCalendarService.create(db, payload, current_user.id)


@router.put("/calendars/{calendar_id}", response_model=HolidayCalendarOut)
def update_calendar(
    calendar_id: int                     = Path(...),
    payload:     HolidayCalendarUpdateIn = ...,
    db:          Session                 = Depends(get_db),
    current_user                         = Depends(get_current_user),
):
    """✏ Edit icon → Edit Holiday Calendar modal → Save."""
    try:
        return HolidayCalendarService.update(db, calendar_id, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc))


@router.delete("/calendars/{calendar_id}", response_model=MessageResponse)
def delete_calendar(
    calendar_id: int     = Path(...),
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """🗑 Trash icon — blocked if it is the default calendar."""
    try:
        HolidayCalendarService.delete(db, calendar_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    return {"message": f"Calendar {calendar_id} deleted."}


# ══════════════════════════════════════════════════════════
# TAB 4 — HOLIDAY SWAP
# ══════════════════════════════════════════════════════════

@router.get("/swaps", response_model=List[SwapRequestOut])
def list_swap_requests(
    employee_id: Optional[str]            = Query(None),
    status_filter:Optional[str]           = Query(None, alias="status",
                                                   description="pending|approved|rejected"),
    db:          Session                  = Depends(get_db),
    current_user                          = Depends(get_current_user),
):
    """
    Holiday Swap tab — Holiday Swap Requests table.
    Columns: Employee · Holiday Date · Work Date · Reason · Status badge · Actions (✓ ✗)
    """
    st = SwapStatusEnum(status_filter) if status_filter else None
    return HolidaySwapService.list(db, employee_id, st)


@router.post("/swaps", response_model=SwapRequestOut,
             status_code=status.HTTP_201_CREATED)
def create_swap_request(
    payload:     SwapRequestIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + New Swap Request button → New Holiday Swap Request modal → Submit.
    Modal fields:
      Employee* · Holiday Date* (work on this holiday)
      Work Date* (take this day off instead) · Reason*
    """
    return HolidaySwapService.create(db, payload, current_user.id)


@router.post("/swaps/{swap_id}/decide", response_model=SwapRequestOut)
def decide_swap(
    swap_id:     int            = Path(...),
    payload:     SwapDecisionIn = ...,
    db:          Session        = Depends(get_db),
    current_user                = Depends(get_current_user),
):
    """
    ✓ Approve / ✗ Reject buttons in the Actions column.
    Only pending requests can be decided.
    """
    try:
        return HolidaySwapService.decide(
            db, swap_id, payload.approved,
            decided_by=getattr(current_user, "name", "HR Admin"),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ══════════════════════════════════════════════════════════
# TAB 5 — CARRY FORWARD
# ══════════════════════════════════════════════════════════

@router.get("/carry-forward", response_model=List[CarryForwardOut])
def list_carry_forward(
    employee_id: Optional[str] = Query(None),
    db:          Session       = Depends(get_db),
    current_user               = Depends(get_current_user),
):
    """
    Carry Forward tab — Holiday Carry Forward table.
    Columns: Employee · From Year · To Year · Holidays (count)
             Status badge · Processed By
    """
    return CarryForwardService.list(db, employee_id)


@router.get("/carry-forward/available-holidays",
            response_model=List[HolidayOut])
def get_available_carry_forward_holidays(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Populates the checkbox list in the Process Carry Forward modal.
    Returns only optional holidays with allowCarryForward=True.
    """
    return CarryForwardService.available_holidays(db)


@router.post("/carry-forward", response_model=CarryForwardOut,
             status_code=status.HTTP_201_CREATED)
def process_carry_forward(
    payload:     CarryForwardIn,
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    + Process Carry Forward button → Process Carry Forward modal → Submit.
    Modal fields:
      Employee* · From Year · To Year
      Unused Optional Holidays (checkbox list — only allowCarryForward=True)
    Validates each selected holiday allows carry forward.
    """
    try:
        return CarryForwardService.process(
            db=db, payload=payload,
            processed_by=current_user.id,
            processed_by_name=getattr(current_user, "name", "HR Admin"),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))


# ══════════════════════════════════════════════════════════
# QUICK ACTIONS  (Today shortcut)
# ══════════════════════════════════════════════════════════

@router.get("/today")
def get_today_holidays(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Quick Actions → Today button.
    Returns holidays on today's date + current month calendar data.
    """
    from models.holiday_calendar import Holiday
    today    = date.today()
    holidays = db.query(Holiday).filter_by(date=today).all()
    from services.holiday_calendar_service import _build_holiday_out
    return {
        "date":         today,
        "isHoliday":    len(holidays) > 0,
        "holidays":     [_build_holiday_out(h) for h in holidays],
        "calendarGrid": CalendarGridService.get_month(db, today.year, today.month),
    }


# ══════════════════════════════════════════════════════════
# STARTUP SEED ENDPOINT  (admin utility)
# ══════════════════════════════════════════════════════════

@router.post("/seed", response_model=MessageResponse)
def seed_defaults(
    db:          Session = Depends(get_db),
    current_user         = Depends(get_current_user),
):
    """
    Seeds: India - National Calendar (default) + 3 national holidays
           (Republic Day, Holi, Independence Day).
    Safe to call multiple times — skips if data already exists.
    Normally called once from the FastAPI startup event, not manually.
    """
    seed_holiday_defaults(db)
    return {"message": "Default holiday data seeded."}


# ── Private helper used by get_holiday ─────────────────────
def _build_out(holiday):
    from services.holiday_calendar_service import _build_holiday_out
    return _build_holiday_out(holiday)
