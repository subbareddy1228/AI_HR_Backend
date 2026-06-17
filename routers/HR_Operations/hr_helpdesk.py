from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from typing import Optional
import io

from core.database import get_db
from model.HR_Operations.hr_helpdesk import Ticket
from schema.HR_Operations.hr_helpdesk import (
    TicketCreate,
    TicketUpdate,
    TicketStart,
    TicketOut,
    TicketListResponse,
    StatsResponse,
    CategoryBreakdownItem,
    AgentPerformanceItem,
    CATEGORIES,
    AGENTS,
)

router = APIRouter(prefix="/hr-ops/helpdesk", tags=["HR Helpdesk"])

# Tickets still Open/In-Progress past this many hours are considered overdue
OVERDUE_THRESHOLD_HOURS = 48


# ---------------------------------------------------------------------------
# Dashboard stats (Total / Open / In Progress / Resolved / High Priority /
# Unassigned / Today's Tickets / Overdue)
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Ticket).count()
    open_count = db.query(Ticket).filter(Ticket.status == "Open").count()
    in_progress = db.query(Ticket).filter(Ticket.status == "In-Progress").count()
    resolved = db.query(Ticket).filter(Ticket.status.in_(["Resolved", "Closed"])).count()
    high_priority = db.query(Ticket).filter(Ticket.priority == "High").count()
    unassigned = db.query(Ticket).filter(Ticket.assigned_agent.is_(None)).count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tickets = db.query(Ticket).filter(Ticket.created_at >= today_start).count()

    overdue_cutoff = datetime.utcnow() - timedelta(hours=OVERDUE_THRESHOLD_HOURS)
    overdue = (
        db.query(Ticket)
        .filter(Ticket.status.in_(["Open", "In-Progress"]))
        .filter(Ticket.created_at <= overdue_cutoff)
        .count()
    )

    return StatsResponse(
        total_tickets=total,
        open=open_count,
        in_progress=in_progress,
        resolved=resolved,
        high_priority=high_priority,
        unassigned=unassigned,
        today_tickets=today_tickets,
        overdue=overdue,
    )


# ---------------------------------------------------------------------------
# Category breakdown sidebar
# ---------------------------------------------------------------------------
@router.get("/category-breakdown", response_model=list[CategoryBreakdownItem])
def get_category_breakdown(db: Session = Depends(get_db)):
    counts = dict(
        db.query(Ticket.category, func.count(Ticket.id))
        .group_by(Ticket.category)
        .all()
    )
    # Ensure every known category appears, even with a 0 count
    return [
        CategoryBreakdownItem(category=cat, count=counts.get(cat, 0))
        for cat in CATEGORIES
    ]


# ---------------------------------------------------------------------------
# Agent performance sidebar
# ---------------------------------------------------------------------------
@router.get("/agent-performance", response_model=list[AgentPerformanceItem])
def get_agent_performance(db: Session = Depends(get_db)):
    results = []
    for agent in AGENTS:
        tickets = db.query(Ticket).filter(Ticket.assigned_agent == agent).all()
        total = len(tickets)
        resolved_tickets = [t for t in tickets if t.status in ("Resolved", "Closed")]
        resolved_count = len(resolved_tickets)

        durations = []
        for t in resolved_tickets:
            start = t.started_at or t.created_at
            if t.resolved_at and start:
                durations.append((t.resolved_at - start).total_seconds() / 3600)

        avg_hours = round(sum(durations) / len(durations), 1) if durations else 0.0

        results.append(
            AgentPerformanceItem(
                agent=agent,
                total=total,
                resolved=resolved_count,
                avg_resolution_hours=avg_hours,
            )
        )
    return results


# ---------------------------------------------------------------------------
# Create ticket
# ---------------------------------------------------------------------------
@router.post("/tickets", response_model=TicketOut)
def create_ticket(payload: TicketCreate, db: Session = Depends(get_db)):
    if payload.category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")
    if payload.priority not in ["Low", "Medium", "High"]:
        raise HTTPException(status_code=400, detail="Invalid priority")

    ticket = Ticket(
        title=payload.title,
        category=payload.category,
        priority=payload.priority,
        employee_name=payload.employee_name,
        description=payload.description,
        status="Open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------------------------------------------------------------------
# List tickets (with filters: category, priority, agent, status, search)
# ---------------------------------------------------------------------------
@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    db: Session = Depends(get_db),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    agent: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    q = db.query(Ticket)

    if category and category != "All Categories":
        q = q.filter(Ticket.category == category)
    if priority and priority != "All Priorities":
        q = q.filter(Ticket.priority == priority)
    if agent and agent != "All Agents":
        q = q.filter(Ticket.assigned_agent == agent)
    if status and status != "All Status":
        q = q.filter(Ticket.status == status)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Ticket.title.ilike(like), Ticket.description.ilike(like)))

    q = q.order_by(Ticket.created_at.desc())
    tickets = q.all()
    return TicketListResponse(total=len(tickets), tickets=tickets)


# ---------------------------------------------------------------------------
# Get single ticket (for "View")
# ---------------------------------------------------------------------------
@router.get("/tickets/{ticket_id}", response_model=TicketOut)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


# ---------------------------------------------------------------------------
# Start ticket (Open -> In-Progress, assign an agent) — the "Start" button
# ---------------------------------------------------------------------------
@router.patch("/tickets/{ticket_id}/start", response_model=TicketOut)
def start_ticket(ticket_id: int, payload: TicketStart, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if payload.assigned_agent not in AGENTS:
        raise HTTPException(status_code=400, detail="Invalid agent")

    ticket.status = "In-Progress"
    ticket.assigned_agent = payload.assigned_agent
    ticket.started_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------------------------------------------------------------------
# Update ticket (general edit, used for resolving / closing / reassigning)
# ---------------------------------------------------------------------------
@router.patch("/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    update_data = payload.dict(exclude_unset=True)

    if "status" in update_data and update_data["status"] == "Resolved" and ticket.status != "Resolved":
        ticket.resolved_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket


# ---------------------------------------------------------------------------
# Delete ticket
# ---------------------------------------------------------------------------
@router.delete("/tickets/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.delete(ticket)
    db.commit()
    return {"message": f"Ticket #{ticket_id} deleted successfully"}


# ---------------------------------------------------------------------------
# Quick Action: Export tickets to Excel
# ---------------------------------------------------------------------------
@router.get("/export")
def export_tickets_to_excel(db: Session = Depends(get_db)):
    try:
        import openpyxl
        from openpyxl.styles import Font
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="openpyxl is required for export. Install with: pip install openpyxl",
        )

    tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"

    headers = [
        "ID", "Title", "Category", "Priority", "Status",
        "Employee Name", "Assigned Agent", "Description",
        "Created At", "Started At", "Resolved At",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for t in tickets:
        ws.append([
            t.id, t.title, t.category, t.priority, t.status,
            t.employee_name, t.assigned_agent, t.description,
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
            t.started_at.strftime("%Y-%m-%d %H:%M") if t.started_at else "",
            t.resolved_at.strftime("%Y-%m-%d %H:%M") if t.resolved_at else "",
        ])

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
        ws.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=hr_helpdesk_tickets.xlsx"},
    )


# ---------------------------------------------------------------------------
# Quick Action: View Unassigned Tickets
# ---------------------------------------------------------------------------
@router.get("/unassigned", response_model=TicketListResponse)
def get_unassigned_tickets(db: Session = Depends(get_db)):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.assigned_agent.is_(None))
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return TicketListResponse(total=len(tickets), tickets=tickets)


# ---------------------------------------------------------------------------
# Quick Action: View All Agents (simple static list with live counts)
# ---------------------------------------------------------------------------
@router.get("/agents")
def get_all_agents(db: Session = Depends(get_db)):
    return {"agents": AGENTS}


# ---------------------------------------------------------------------------
# Quick Action: Generate Weekly Report
# ---------------------------------------------------------------------------
@router.get("/weekly-report")
def generate_weekly_report(db: Session = Depends(get_db)):
    week_start = datetime.utcnow() - timedelta(days=7)
    tickets = db.query(Ticket).filter(Ticket.created_at >= week_start).all()

    resolved_this_week = [t for t in tickets if t.status in ("Resolved", "Closed")]

    by_category = {}
    by_priority = {"Low": 0, "Medium": 0, "High": 0}
    for t in tickets:
        by_category[t.category] = by_category.get(t.category, 0) + 1
        by_priority[t.priority] = by_priority.get(t.priority, 0) + 1

    return {
        "period": {
            "from": week_start.strftime("%Y-%m-%d"),
            "to": datetime.utcnow().strftime("%Y-%m-%d"),
        },
        "total_tickets_created": len(tickets),
        "total_resolved": len(resolved_this_week),
        "by_category": by_category,
        "by_priority": by_priority,
    }