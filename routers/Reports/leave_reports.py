from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from core.database import get_db
from typing import Optional
from datetime import date

try:
    from model.models import LeaveRequest
except ImportError:
    LeaveRequest = None

router = APIRouter(prefix="/leave", tags=["Reports"])


@router.get("/summary")
def leave_summary(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if LeaveRequest is None:
        return {
            "total_leaves": 0,
            "by_leave_type": {},
            "by_status": {},
            "message": "LeaveRequest model not available",
        }

    query = select(LeaveRequest)
    if start_date:
        query = query.where(LeaveRequest.start_date >= start_date)
    if end_date:
        query = query.where(LeaveRequest.end_date <= end_date)
    if employee_id:
        query = query.where(LeaveRequest.employee_id == employee_id)

    leaves = db.execute(query).scalars().all()

    by_type: dict = {}
    by_status: dict = {}
    for leave in leaves:
        lt = leave.leave_type or "Unknown"
        by_type[lt] = by_type.get(lt, 0) + 1

        st = leave.status or "Unknown"
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "total_leaves": len(leaves),
        "by_leave_type": by_type,
        "by_status": by_status,
    }


@router.get("/pending-approvals")
def pending_approvals(db: Session = Depends(get_db)):
    if LeaveRequest is None:
        return {"count": 0, "data": [], "message": "LeaveRequest model not available"}

    leaves = db.execute(
        select(LeaveRequest).where(LeaveRequest.status == "Pending")
    ).scalars().all()

    data = [
        {
            "id": leave.id,
            "leave_type": leave.leave_type,
            "start_date": str(leave.start_date) if leave.start_date else None,
            "end_date": str(leave.end_date) if leave.end_date else None,
            "status": leave.status,
        }
        for leave in leaves
    ]
    return {"count": len(data), "data": data}


@router.get("/utilization")
def leave_utilization(
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    if LeaveRequest is None:
        return {
            "year": year,
            "monthly_utilization": [],
            "message": "LeaveRequest model not available",
        }

    rows = db.execute(
        select(
            func.extract("month", LeaveRequest.start_date).label("month"),
            func.count(LeaveRequest.id).label("leave_count"),
        )
        .where(
            func.extract("year", LeaveRequest.start_date) == year,
            LeaveRequest.status == "Approved",
        )
        .group_by(func.extract("month", LeaveRequest.start_date))
        .order_by(func.extract("month", LeaveRequest.start_date))
    ).all()

    monthly: dict = {m: 0 for m in range(1, 13)}
    for row in rows:
        monthly[int(row.month)] = row.leave_count

    return {
        "year": year,
        "monthly_utilization": [
            {"month": m, "leave_count": count} for m, count in monthly.items()
        ],
    }
