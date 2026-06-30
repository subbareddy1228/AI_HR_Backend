import csv
import io
from datetime import datetime, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.hr_helpdesk import HRHelpdesk
from schema.HR_Operations.hr_helpdesk import (
    HRHelpdeskCreate,
    HRHelpdeskUpdate,
    HRHelpdeskResponse,
    TicketAssignPayload,
    TicketResolvePayload,
    HelpdeskStatCards,
    CategoryBreakdownItem,
    CategoryBreakdownResponse,
    AgentPerformanceItem,
    AgentPerformanceResponse,
    WeeklyReportResponse,
)

router = APIRouter(prefix="/helpdesk", tags=["HR Helpdesk & Ticketing"])





ALL_CATEGORIES = [
    "Payroll queries",
    "Leave and attendance issues",
    "Policy clarifications",
    "IT access issues",
    "Document requests",
    "Reimbursement queries",
    "Personal data updates",
    "General HR queries",
    "Grievances and complaints",
]


def _get_or_404(ticket_id: int, db: Session) -> HRHelpdesk:
    record = db.query(HRHelpdesk).filter(HRHelpdesk.id == ticket_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Ticket #{ticket_id} not found.")
    return record


def _is_overdue(record: HRHelpdesk) -> bool:
    
    if record.due_date and record.status not in ("RESOLVED", "CLOSED"):
        return record.due_date < date.today()
    return False


def _build_category_counts(records: list) -> dict:
    counts = {cat: 0 for cat in ALL_CATEGORIES}
    for r in records:
        if r.category in counts:
            counts[r.category] += 1
        else:
            counts[r.category] = counts.get(r.category, 0) + 1
    return counts


def _build_agent_items(records: list) -> List[AgentPerformanceItem]:
    agent_map: dict = {}
    for r in records:
        if not r.assigned_agent:
            continue
        entry = agent_map.setdefault(
            r.assigned_agent,
            {"total": 0, "resolved": 0, "in_progress": 0, "open": 0},
        )
        entry["total"] += 1
        if r.status == "RESOLVED":
            entry["resolved"] += 1
        elif r.status == "IN_PROGRESS":
            entry["in_progress"] += 1
        elif r.status == "OPEN":
            entry["open"] += 1

    return [
        AgentPerformanceItem(
            agent_name=name,
            total=v["total"],
            resolved=v["resolved"],
            in_progress=v["in_progress"],
            open=v["open"],
        )
        for name, v in sorted(agent_map.items(), key=lambda x: -x[1]["total"])
    ]




@router.get(
    "/stats",
    response_model=HelpdeskStatCards,
    summary="Stat cards: Total, Open, In-Progress, Resolved, High Priority, Unassigned, Today, Overdue",
)
def get_stats(db: Session = Depends(get_db)):
    records = db.query(HRHelpdesk).all()
    today   = date.today()

    return HelpdeskStatCards(
        total_tickets  = len(records),
        open           = sum(1 for r in records if r.status == "OPEN"),
        in_progress    = sum(1 for r in records if r.status == "IN_PROGRESS"),
        resolved       = sum(1 for r in records if r.status == "RESOLVED"),
        high_priority  = sum(1 for r in records if r.priority in ("HIGH", "URGENT")),
        unassigned     = sum(1 for r in records if not r.assigned_to and not r.assigned_agent),
        todays_tickets = sum(1 for r in records if r.created_at and r.created_at.date() == today),
        overdue        = sum(1 for r in records if _is_overdue(r)),
    )



@router.get(
    "/analytics/categories",
    response_model=CategoryBreakdownResponse,
    summary="Category Breakdown sidebar – ticket count per category",
)
def category_breakdown(db: Session = Depends(get_db)):
    
    records = db.query(HRHelpdesk).all()
    counts  = _build_category_counts(records)
    items   = [CategoryBreakdownItem(category=cat, count=counts.get(cat, 0)) for cat in ALL_CATEGORIES]
    return CategoryBreakdownResponse(items=items)


@router.get(
    "/analytics/agents",
    response_model=AgentPerformanceResponse,
    summary="Agent Performance sidebar – ticket counts per agent",
)
def agent_performance(db: Session = Depends(get_db)):
    
    records = db.query(HRHelpdesk).all()
    return AgentPerformanceResponse(agents=_build_agent_items(records))



@router.get(
    "/analytics/unassigned",
    response_model=List[HRHelpdeskResponse],
    summary="[Quick Action] View Unassigned Tickets",
)
def view_unassigned_tickets(db: Session = Depends(get_db)):
    
    return (
        db.query(HRHelpdesk)
        .filter(HRHelpdesk.assigned_to.is_(None), HRHelpdesk.assigned_agent.is_(None))
        .order_by(HRHelpdesk.created_at.desc())
        .all()
    )


@router.get(
    "/analytics/weekly-report",
    response_model=WeeklyReportResponse,
    summary="[Quick Action] Generate Weekly Report",
)
def generate_weekly_report(db: Session = Depends(get_db)):
    
    today      = date.today()
    week_start = today - timedelta(days=today.weekday())      
    week_end   = week_start + timedelta(days=6)               

    all_records  = db.query(HRHelpdesk).all()
    week_records = [
        r for r in all_records
        if r.created_at and r.created_at.date() >= week_start
    ]

    resolved_this_week = [
        r for r in week_records if r.status in ("RESOLVED", "CLOSED")
    ]

    
    res_hours = []
    for r in resolved_this_week:
        if r.resolved_at and r.created_at:
            delta = (r.resolved_at - r.created_at).total_seconds() / 3600
            res_hours.append(delta)
    avg_res_hrs = round(sum(res_hours) / len(res_hours), 1) if res_hours else 0.0

    
    cat_counts = _build_category_counts(week_records)
    top_cat    = max(cat_counts, key=cat_counts.get) if cat_counts else None

    return WeeklyReportResponse(
        week_start         = week_start,
        week_end           = week_end,
        tickets_created    = len(week_records),
        tickets_resolved   = sum(1 for r in week_records if r.status == "RESOLVED"),
        tickets_closed     = sum(1 for r in week_records if r.status == "CLOSED"),
        avg_resolution_hrs = avg_res_hrs,
        top_category       = top_cat,
        unresolved_count   = sum(1 for r in all_records if r.status in ("OPEN", "IN_PROGRESS")),
        overdue_count      = sum(1 for r in all_records if _is_overdue(r)),
        agent_breakdown    = _build_agent_items(all_records),
        category_breakdown = [
            CategoryBreakdownItem(category=cat, count=cnt)
            for cat, cnt in cat_counts.items()
        ],
    )


@router.get(
    "/analytics/export",
    summary="[Quick Action] Export Tickets to Excel / CSV",
)
def export_tickets_csv(db: Session = Depends(get_db)):
    
    records = db.query(HRHelpdesk).order_by(HRHelpdesk.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Ticket ID", "Title", "Category", "Priority", "Status",
        "Employee ID", "Employee Name", "Assigned Agent",
        "Description", "Resolution",
        "Due Date", "Resolved At", "Created At", "Updated At",
    ])
    for r in records:
        writer.writerow([
            f"#{r.id}",
            r.title,
            r.category,
            r.priority,
            r.status,
            r.employee_id    or "",
            r.employee_name  or "",
            r.assigned_agent or "",
            r.description,
            r.resolution     or "",
            str(r.due_date)  if r.due_date    else "",
            r.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if r.resolved_at else "",
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at  else "",
            r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at  else "",
        ])

    output.seek(0)
    filename = f"hr_helpdesk_export_{date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/agents",
    summary="[Quick Action] View All Agents – list of agents and their ticket counts",
)
def view_all_agents(db: Session = Depends(get_db)):
    
    records = db.query(HRHelpdesk).all()
    return {"agents": _build_agent_items(records)}



@router.get(
    "/",
    response_model=List[HRHelpdeskResponse],
    summary="All Tickets table with search, category, priority, agent, status filters",
)
def list_tickets(
    search:   Optional[str] = Query(None, description="Free-text: title or description"),
    category: Optional[str] = Query(None, description="Category filter – 'All Categories' = omit"),
    priority: Optional[str] = Query(None, description="LOW | MEDIUM | HIGH | URGENT"),
    agent:    Optional[str] = Query(None, description="Agent display name filter"),
    status:   Optional[str] = Query(None, description="OPEN | IN_PROGRESS | RESOLVED | CLOSED"),
    skip:     int = Query(0, ge=0),
    limit:    int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(HRHelpdesk)

    if search:
        like = f"%{search}%"
        q = q.filter(
            HRHelpdesk.title.ilike(like) | HRHelpdesk.description.ilike(like)
        )
    if category:
        q = q.filter(HRHelpdesk.category == category)
    if priority:
        q = q.filter(HRHelpdesk.priority == priority.upper())
    if agent:
        q = q.filter(HRHelpdesk.assigned_agent.ilike(f"%{agent}%"))
    if status:
        q = q.filter(HRHelpdesk.status == status.upper().replace("-", "_").replace(" ", "_"))

    return q.order_by(HRHelpdesk.created_at.desc()).offset(skip).limit(limit).all()




@router.post(
    "/",
    response_model=HRHelpdeskResponse,
    status_code=201,
    summary="Create a new support ticket",
)
def create_ticket(payload: HRHelpdeskCreate, db: Session = Depends(get_db)):
    
    record = HRHelpdesk(**payload.model_dump(), status="OPEN")
    db.add(record)
    db.commit()
    db.refresh(record)
    return record




@router.get(
    "/{ticket_id}",
    response_model=HRHelpdeskResponse,
    summary="View a single ticket (View button)",
)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    return _get_or_404(ticket_id, db)


@router.patch(
    "/{ticket_id}",
    response_model=HRHelpdeskResponse,
    summary="Update ticket fields (edit pencil icon)",
)
def update_ticket(
    ticket_id: int,
    payload: HRHelpdeskUpdate,
    db: Session = Depends(get_db),
):
    record  = _get_or_404(ticket_id, db)
    updates = payload.model_dump(exclude_unset=True)

    
    if updates.get("status") == "RESOLVED" and not record.resolved_at:
        updates["resolved_at"] = datetime.utcnow()

    for key, value in updates.items():
        setattr(record, key, value)

    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.delete(
    "/{ticket_id}",
    summary="Delete a ticket",
)
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    record = _get_or_404(ticket_id, db)
    db.delete(record)
    db.commit()
    return {"message": f"Ticket #{ticket_id} deleted successfully."}




@router.post(
    "/{ticket_id}/start",
    response_model=HRHelpdeskResponse,
    summary="[Action] Start button – assign agent and set IN_PROGRESS",
)
def start_ticket(
    ticket_id: int,
    payload: TicketAssignPayload,
    db: Session = Depends(get_db),
):
    record = _get_or_404(ticket_id, db)
    if record.status not in ("OPEN",):
        raise HTTPException(
            status_code=400,
            detail=f"Ticket is '{record.status}'. Only OPEN tickets can be started.",
        )
    record.status         = "IN_PROGRESS"
    record.assigned_to    = payload.assigned_to    or record.assigned_to
    record.assigned_agent = payload.assigned_agent or record.assigned_agent
    record.updated_at     = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.post(
    "/{ticket_id}/resolve",
    response_model=HRHelpdeskResponse,
    summary="[Action] Resolve – mark ticket as RESOLVED with resolution notes",
)
def resolve_ticket(
    ticket_id: int,
    payload: TicketResolvePayload,
    db: Session = Depends(get_db),
):
    record = _get_or_404(ticket_id, db)
    if record.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=400,
            detail=f"Ticket is '{record.status}'. Only IN_PROGRESS tickets can be resolved.",
        )
    record.status      = "RESOLVED"
    record.resolution  = payload.resolution
    record.resolved_at = datetime.utcnow()
    record.updated_at  = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.post(
    "/{ticket_id}/close",
    response_model=HRHelpdeskResponse,
    summary="[Action] Close – mark ticket as CLOSED",
)
def close_ticket(ticket_id: int, db: Session = Depends(get_db)):
   
    record = _get_or_404(ticket_id, db)
    if record.status not in ("RESOLVED", "OPEN", "IN_PROGRESS"):
        raise HTTPException(
            status_code=400,
            detail=f"Ticket is already '{record.status}'.",
        )
    record.status     = "CLOSED"
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record


@router.post(
    "/{ticket_id}/reopen",
    response_model=HRHelpdeskResponse,
    summary="[Action] Reopen – move a CLOSED or RESOLVED ticket back to OPEN",
)
def reopen_ticket(ticket_id: int, db: Session = Depends(get_db)):
    
    record = _get_or_404(ticket_id, db)
    if record.status not in ("CLOSED", "RESOLVED"):
        raise HTTPException(
            status_code=400,
            detail=f"Ticket is '{record.status}'. Only CLOSED or RESOLVED tickets can be reopened.",
        )
    record.status      = "OPEN"
    record.resolved_at = None
    record.updated_at  = datetime.utcnow()
    db.commit()
    db.refresh(record)
    return record