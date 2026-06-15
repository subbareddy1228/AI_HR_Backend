from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import Optional
from datetime import date, datetime
import json

from core.database import get_db

from model.onboarding.employee                   import Employee
from model.Employee_Management.employee_master   import EmployeeMaster
from model.Employee_Management.employee_document import EmployeeDocument
from model.Employee_Management.employee_lifecycle import (
    EmployeeLifecycleEvent, TransferRequest, ExitProcess, OnboardingTask
)
from model.Payroll.salary_slip                   import SalarySlip
from model.Payroll.loan_advance                  import LoanAdvance
from model.Payroll.reimbursement                 import Reimbursement
from model.HR_Operations.hr_helpdesk             import HRHelpdesk
# from model.models import AttendanceRecord, LeaveRequest, LeaveStatus
from model.HR_Automation.attendance_capture import AttendanceRecord
from model.models import LeaveRequest, LeaveStatus
router = APIRouter(prefix="/self-service", tags=["Employee Self Service"])



@router.get("/{employee_id}/dashboard")
def get_dashboard(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    today   = date.today()
    m_start = today.replace(day=1)

    
    present_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date        >= m_start,
            AttendanceRecord.status      == "Present",
        )
        .scalar() or 0
    )
    absent_days = (
        db.query(func.count(AttendanceRecord.id))
        .filter(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date        >= m_start,
            AttendanceRecord.status      == "Absent",
        )
        .scalar() or 0
    )

    
    leave_this_month = (
        db.query(func.count(LeaveRequest.id))
        .filter(
            LeaveRequest.start_date >= m_start,
        )
        .scalar() or 0
    )
    pending_leaves = (
        db.query(func.count(LeaveRequest.id))
        .filter(LeaveRequest.status == LeaveStatus.pending)
        .scalar() or 0
    )

    
    latest_slip = (
        db.execute(
            select(SalarySlip)
            .where(SalarySlip.employee_id == employee_id)
            .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
        ).scalars().first()
    )

    
    open_tickets = (
        db.query(func.count(HRHelpdesk.id))
        .filter(
            HRHelpdesk.employee_id == employee_id,
            HRHelpdesk.status.in_(["OPEN", "IN_PROGRESS"]),
        )
        .scalar() or 0
    )

    active_loans = (
        db.query(func.count(LoanAdvance.id))
        .filter(
            LoanAdvance.employee_id == employee_id,
            LoanAdvance.status.in_(["Pending", "Active"]),
        )
        .scalar() or 0
    )

    tenure_days = (today - emp.joining_date).days if emp.joining_date else 0

    return {
        "profile": {
            "id":            emp.id,
            "name":          f"{emp.first_name} {emp.last_name or ''}".strip(),
            "employeeCode":  emp.employee_code,
            "department":    emp.department,
            "designation":   emp.designation,
            "location":      emp.location,
            "grade":         emp.grade,
            "joiningDate":   str(emp.joining_date),
            "tenure":        f"{round(tenure_days / 365, 1)} years",
            "isActive":      emp.is_active,
        },
        "attendance": {
            "presentDaysThisMonth": present_days,
            "absentDaysThisMonth":  absent_days,
        },
        "leaves": {
            "appliedThisMonth": leave_this_month,
            "pendingApprovals": pending_leaves,
        },
        "latestPayslip": {
            "month":          latest_slip.slip_month if latest_slip else None,
            "year":           latest_slip.slip_year  if latest_slip else None,
            "netPay":         float(latest_slip.net_pay) if latest_slip else None,
            "isPublished":    latest_slip.is_published  if latest_slip else False,
        } if latest_slip else None,
        "openTickets":  open_tickets,
        "activeLoans":  active_loans,
    }




@router.get("/{employee_id}/profile")
def get_self_profile(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    master = db.execute(
        select(EmployeeMaster).where(EmployeeMaster.employee_id == employee_id)
    ).scalar_one_or_none()

    profile = {
        "id":                emp.id,
        "employeeCode":      emp.employee_code,
        "firstName":         emp.first_name,
        "middleName":        emp.middle_name,
        "lastName":          emp.last_name,
        "dateOfBirth":       str(emp.date_of_birth)    if emp.date_of_birth    else None,
        "gender":            emp.gender.value          if emp.gender           else None,
        "officialEmail":     emp.official_email,
        "mobileNumber":      emp.mobile_number,
        "joiningDate":       str(emp.joining_date)     if emp.joining_date     else None,
        "confirmationDate":  str(emp.confirmation_date) if emp.confirmation_date else None,
        "department":        emp.department,
        "designation":       emp.designation,
        "businessUnit":      emp.business_unit,
        "location":          emp.location,
        "grade":             emp.grade,
        "isActive":          emp.is_active,
    }

    if master:
        profile.update({
            "employmentType":      master.employment_type,
            "employmentStatus":    master.employment_status,
            "workLocation":        master.work_location,
            "probationEndDate":    str(master.probation_end_date) if master.probation_end_date else None,
            "confirmedDate":       str(master.confirmed_date)     if master.confirmed_date     else None,
            "noticePeriodDays":    master.notice_period_days,
            "reportingManagerId":  master.reporting_manager_id,
        })

    return profile


@router.patch("/{employee_id}/profile")
def update_self_profile(
    employee_id: int,
    mobile_number: Optional[str] = None,
    official_email: Optional[str] = None,
    db: Session = Depends(get_db),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if mobile_number:
        emp.mobile_number = mobile_number
    if official_email:
        emp.official_email = official_email

    db.commit()
    db.refresh(emp)
    return {"message": "Profile updated successfully", "employeeId": employee_id}



@router.get("/{employee_id}/attendance")
def get_self_attendance(
    employee_id: int,
    db:          Session        = Depends(get_db),
    year:        int            = Query(default=None),
    month:       int            = Query(default=None),
):
    today  = date.today()
    year   = year  or today.year
    month  = month or today.month
    m_start = date(year, month, 1)
    m_end   = date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)

    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    records = db.execute(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date        >= m_start,
            AttendanceRecord.date        <  m_end,
        )
        .order_by(AttendanceRecord.date)
    ).scalars().all()


    status_counts: dict = {}
    for r in records:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    return {
        "month":   month,
        "year":    year,
        "summary": {
            "present":  status_counts.get("Present",  0),
            "absent":   status_counts.get("Absent",   0),
            "late":     status_counts.get("Late",     0),
            "halfDay":  status_counts.get("Half Day", 0),
            "total":    len(records),
        },
        "records": [
            {
                "id":       r.id,
                "date":     str(r.date),
                "status":   r.status,
                "checkIn":  r.check_in,
                "checkOut": r.check_out,
                "remarks":  r.remarks,
            }
            for r in records
        ],
    }


@router.get("/{employee_id}/leaves")
def get_self_leaves(
    employee_id: int,
    db:          Session        = Depends(get_db),
    status:      Optional[str] = Query(None),
    year:        int            = Query(default=None),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    today = date.today()
    year  = year or today.year
    m_start = date(year, 1, 1)
    m_end   = date(year + 1, 1, 1)

    q = select(LeaveRequest).where(
        LeaveRequest.start_date >= m_start,
        LeaveRequest.start_date <  m_end,
    )
    if status:
        q = q.where(LeaveRequest.status == status)
    q = q.order_by(LeaveRequest.start_date.desc())

    leaves = db.execute(q).scalars().all()

    return {
        "year": year,
        "total": len(leaves),
        "leaves": [
            {
                "id":        l.id,
                "leaveType": l.leave_type,
                "startDate": str(l.start_date),
                "endDate":   str(l.end_date),
                "reason":    l.reason,
                "status":    l.status.value if hasattr(l.status, "value") else l.status,
            }
            for l in leaves
        ],
    }


@router.post("/{employee_id}/leaves")
def apply_leave(
    employee_id: int,
    leave_type:  str,
    start_date:  date,
    end_date:    date,
    reason:      Optional[str] = None,
    db:          Session       = Depends(get_db),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date cannot be before start date")

    leave = LeaveRequest(
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        reason=reason,
        status=LeaveStatus.pending,
    )
    db.add(leave)
    db.commit()
    db.refresh(leave)
    return {
        "message":   "Leave applied successfully",
        "leaveId":   leave.id,
        "status":    leave.status.value,
        "leaveType": leave.leave_type,
        "startDate": str(leave.start_date),
        "endDate":   str(leave.end_date),
    }


@router.get("/{employee_id}/payslips")
def get_self_payslips(
    employee_id: int,
    db:          Session = Depends(get_db),
    year:        int     = Query(default=None),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    q = select(SalarySlip).where(SalarySlip.employee_id == employee_id)
    if year:
        q = q.where(SalarySlip.slip_year == year)
    q = q.order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())

    slips = db.execute(q).scalars().all()

    MONTHS = ["","Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    return {
        "total": len(slips),
        "slips": [
            {
                "id":              s.id,
                "period":          f"{MONTHS[s.slip_month]} {s.slip_year}",
                "month":           s.slip_month,
                "year":            s.slip_year,
                "grossSalary":     float(s.gross_salary),
                "totalDeductions": float(s.total_deductions),
                "netPay":          float(s.net_pay),
                "isPublished":     s.is_published,
                "generatedAt":     str(s.generated_at) if s.generated_at else None,
                "earnings":        json.loads(s.earnings_json)    if s.earnings_json    else {},
                "deductions":      json.loads(s.deductions_json)  if s.deductions_json  else {},
            }
            for s in slips
        ],
    }


@router.get("/{employee_id}/payslips/{slip_id}")
def get_payslip_detail(
    employee_id: int,
    slip_id:     int,
    db:          Session = Depends(get_db),
):
    slip = db.execute(
        select(SalarySlip).where(
            SalarySlip.id          == slip_id,
            SalarySlip.employee_id == employee_id,
        )
    ).scalars().first()
    if not slip:
        raise HTTPException(status_code=404, detail="Payslip not found")

    MONTHS = ["","Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]

    return {
        "id":              slip.id,
        "period":          f"{MONTHS[slip.slip_month]} {slip.slip_year}",
        "employeeCode":    slip.employee_code,
        "employeeName":    slip.employee_name,
        "department":      slip.department,
        "designation":     slip.designation,
        "bankAccount":     slip.bank_account,
        "bankName":        slip.bank_name,
        "grossSalary":     float(slip.gross_salary),
        "totalDeductions": float(slip.total_deductions),
        "netPay":          float(slip.net_pay),
        "isPublished":     slip.is_published,
        "generatedAt":     str(slip.generated_at) if slip.generated_at else None,
        "earnings":        json.loads(slip.earnings_json)   if slip.earnings_json   else {},
        "deductions":      json.loads(slip.deductions_json) if slip.deductions_json else {},
    }


@router.get("/{employee_id}/documents")
def get_self_documents(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    docs = db.execute(
        select(EmployeeDocument).where(EmployeeDocument.employee_id == employee_id)
    ).scalars().all()

    return [
        {
            "id":           doc.id,
            "documentType": doc.document_type,
            "documentName": doc.document_name,
            "filePath":     doc.file_path,
            "uploadedAt":   str(doc.uploaded_at) if doc.uploaded_at else None,
            "isVerified":   doc.is_verified,
            "verifiedBy":   doc.verified_by,
            "notes":        doc.notes,
        }
        for doc in docs
    ]



@router.get("/{employee_id}/loans")
def get_self_loans(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    loans = db.execute(
        select(LoanAdvance)
        .where(LoanAdvance.employee_id == employee_id)
        .order_by(LoanAdvance.created_at.desc())
    ).scalars().all()

    return [
        {
            "id":                l.id,
            "loanType":         l.loan_type,
            "amount":           float(l.amount),
            "approvedAmount":   float(l.approved_amount) if l.approved_amount else None,
            "emiAmount":        float(l.emi_amount)      if l.emi_amount      else None,
            "totalInstallments":l.total_installments,
            "paidInstallments": l.paid_installments,
            "startDate":        str(l.start_date)        if l.start_date      else None,
            "status":           l.status,
            "reason":           l.reason,
            "approvedBy":       l.approved_by,
            "createdAt":        str(l.created_at),
        }
        for l in loans
    ]


@router.post("/{employee_id}/loans")
def apply_loan(
    employee_id: int,
    loan_type:   str,
    amount:      float,
    reason:      Optional[str] = None,
    db:          Session       = Depends(get_db),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    loan = LoanAdvance(
        employee_id=employee_id,
        loan_type=loan_type,
        amount=amount,
        reason=reason,
        status="Pending",
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return {
        "message":  "Loan application submitted",
        "loanId":   loan.id,
        "loanType": loan.loan_type,
        "amount":   float(loan.amount),
        "status":   loan.status,
    }



@router.get("/{employee_id}/reimbursements")
def get_self_reimbursements(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    claims = db.execute(
        select(Reimbursement)
        .where(Reimbursement.employee_id == employee_id)
        .order_by(Reimbursement.created_at.desc())
    ).scalars().all()

    return [
        {
            "id":          c.id,
            "claimType":   c.claim_type,
            "amount":      float(c.amount),
            "claimDate":   str(c.claim_date),
            "description": c.description,
            "status":      c.status,
            "approvedBy":  c.approved_by,
            "remarks":     c.remarks,
            "createdAt":   str(c.created_at),
        }
        for c in claims
    ]


@router.post("/{employee_id}/reimbursements")
def submit_reimbursement(
    employee_id:  int,
    claim_type:   str,
    amount:       float,
    claim_date:   date,
    description:  Optional[str] = None,
    db:           Session       = Depends(get_db),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    claim = Reimbursement(
        employee_id=employee_id,
        claim_type=claim_type,
        amount=amount,
        claim_date=claim_date,
        description=description,
        status="Pending",
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return {
        "message":   "Reimbursement claim submitted",
        "claimId":   claim.id,
        "claimType": claim.claim_type,
        "amount":    float(claim.amount),
        "status":    claim.status,
    }



@router.get("/{employee_id}/helpdesk")
def get_self_tickets(
    employee_id: int,
    db:          Session        = Depends(get_db),
    status:      Optional[str] = Query(None),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    q = select(HRHelpdesk).where(HRHelpdesk.employee_id == employee_id)
    if status:
        q = q.where(HRHelpdesk.status == status)
    q = q.order_by(HRHelpdesk.created_at.desc())

    tickets = db.execute(q).scalars().all()

    return [
        {
            "id":          t.id,
            "category":    t.category,
            "subject":     t.subject,
            "description": t.description,
            "priority":    t.priority,
            "status":      t.status,
            "resolution":  t.resolution,
            "resolvedAt":  str(t.resolved_at) if t.resolved_at else None,
            "createdAt":   str(t.created_at),
        }
        for t in tickets
    ]


@router.post("/{employee_id}/helpdesk")
def raise_ticket(
    employee_id: int,
    category:    str,
    subject:     str,
    description: str,
    priority:    str = "MEDIUM",
    db:          Session = Depends(get_db),
):
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    ticket = HRHelpdesk(
        employee_id=employee_id,
        category=category,
        subject=subject,
        description=description,
        priority=priority,
        status="OPEN",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {
        "message":   "Ticket raised successfully",
        "ticketId":  ticket.id,
        "category":  ticket.category,
        "subject":   ticket.subject,
        "priority":  ticket.priority,
        "status":    ticket.status,
    }


@router.get("/{employee_id}/transfers")
def get_self_transfers(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    transfers = db.execute(
        select(TransferRequest)
        .where(TransferRequest.employee_id == employee_id)
        .order_by(TransferRequest.created_at.desc())
    ).scalars().all()

    return [
        {
            "id":             t.id,
            "transferType":   t.transfer_type,
            "fromDepartment": t.from_department,
            "toDepartment":   t.to_department,
            "fromLocation":   t.from_location,
            "toLocation":     t.to_location,
            "requestDate":    str(t.request_date),
            "effectiveDate":  str(t.effective_date) if t.effective_date else None,
            "status":         t.status,
            "remarks":        t.remarks,
        }
        for t in transfers
    ]


@router.get("/{employee_id}/lifecycle")
def get_self_lifecycle(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    events = db.execute(
        select(EmployeeLifecycleEvent)
        .where(EmployeeLifecycleEvent.employee_id == employee_id,
               EmployeeLifecycleEvent.is_active   == True)
        .order_by(EmployeeLifecycleEvent.event_date.desc())
    ).scalars().all()

    return [
        {
            "id":               evt.id,
            "eventType":        evt.event_type,
            "eventDate":        str(evt.event_date),
            "effectiveDate":    str(evt.effective_date) if evt.effective_date else None,
            "fromValue":        evt.from_value,
            "toValue":          evt.to_value,
            "fromDepartment":   evt.from_department,
            "toDepartment":     evt.to_department,
            "fromDesignation":  evt.from_designation,
            "toDesignation":    evt.to_designation,
            "fromGrade":        evt.from_grade,
            "toGrade":          evt.to_grade,
            "fromLocation":     evt.from_location,
            "toLocation":       evt.to_location,
            "fromSalary":       evt.from_salary,
            "toSalary":         evt.to_salary,
            "approvalStatus":   evt.approval_status,
            "remarks":          evt.remarks,
        }
        for evt in events
    ]



@router.get("/{employee_id}/onboarding-tasks")
def get_self_onboarding_tasks(employee_id: int, db: Session = Depends(get_db)):
    
    emp = db.execute(
        select(Employee).where(Employee.id == employee_id)
    ).scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    tasks = db.execute(
        select(OnboardingTask)
        .where(OnboardingTask.employee_id == employee_id,
               OnboardingTask.is_active   == True)
        .order_by(OnboardingTask.due_date)
    ).scalars().all()

    return {
        "total":     len(tasks),
        "pending":   sum(1 for t in tasks if t.status == "pending"),
        "completed": sum(1 for t in tasks if t.status == "completed"),
        "tasks": [
            {
                "id":          t.id,
                "task":        t.task,
                "assignedTo":  t.assigned_to,
                "dueDate":     str(t.due_date) if t.due_date else None,
                "status":      t.status,
                "completedAt": str(t.completed_at) if t.completed_at else None,
                "remarks":     t.remarks,
            }
            for t in tasks
        ],
    }
