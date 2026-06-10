# """
# Router: HR Letters
# Prefix : /api/hr-letters
# Covers : Templates CRUD + Issue / Send / Revoke letters + PDF generation
# """

# from typing import List, Optional
# from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
# from sqlmodel import Session

# from schema.HR_Operations.letter_generation import (
#     HRLetterTemplateCreate, HRLetterTemplateUpdate, HRLetterTemplateResponse,
#     HRLetterIssueRequest, HRLetterStatusUpdate, HRLetterResponse,
#     SendLetterEmailRequest,
# )
# from model.HR_Operations.letter_generation import LetterType, LetterStatus
# from services.letters_service import HRLetterService
# from core.dependencies import get_db, get_current_user, require_roles

# router = APIRouter(prefix="/api/hr-letters", tags=["HR Letters"])


# # ═══════════════════════════════════════════════════════════════════════════════
# #  LETTER TEMPLATES
# # ═══════════════════════════════════════════════════════════════════════════════

# @router.post(
#     "/templates",
#     response_model=HRLetterTemplateResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Create HR letter template",
# )
# def create_template(
#     payload: HRLetterTemplateCreate,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     """
#     Create a reusable letter template.
#     Body uses Jinja2 syntax — e.g. {{ employee_name }}.
#     """
#     return HRLetterService.create_template(db, payload, current_user.id)


# @router.get(
#     "/templates",
#     response_model=List[HRLetterTemplateResponse],
#     summary="List all active HR letter templates",
# )
# def list_templates(
#     letter_type: Optional[LetterType] = None,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin", "admin"])),
# ):
#     return HRLetterService.list_templates(db, letter_type=letter_type)


# @router.get(
#     "/templates/{template_id}",
#     response_model=HRLetterTemplateResponse,
#     summary="Get a specific letter template",
# )
# def get_template(
#     template_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin", "admin"])),
# ):
#     template = HRLetterService.get_template(db, template_id)
#     if not template:
#         raise HTTPException(status_code=404, detail="Template not found")
#     return template


# @router.put(
#     "/templates/{template_id}",
#     response_model=HRLetterTemplateResponse,
#     summary="Update a letter template",
# )
# def update_template(
#     template_id: int,
#     payload: HRLetterTemplateUpdate,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     return HRLetterService.update_template(db, template_id, payload)


# @router.delete(
#     "/templates/{template_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
#     summary="Delete (soft-delete) a letter template",
# )
# def delete_template(
#     template_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     HRLetterService.delete_template(db, template_id)


# # ═══════════════════════════════════════════════════════════════════════════════
# #  ISSUED LETTERS
# # ═══════════════════════════════════════════════════════════════════════════════

# @router.post(
#     "/issue",
#     response_model=HRLetterResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Issue a letter to an employee",
# )
# def issue_letter(
#     payload: HRLetterIssueRequest,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     """
#     Issue (create a draft) of a letter for an employee.
#     If template_id is provided, variables are merged automatically.
#     Triggers async PDF generation in the background.
#     """
#     letter = HRLetterService.issue_letter(db, payload, current_user.id)
#     background_tasks.add_task(HRLetterService.generate_pdf, db, letter.id)
#     return letter


# @router.get(
#     "/",
#     response_model=List[HRLetterResponse],
#     summary="List all issued letters (HR Admin)",
# )
# def list_letters(
#     employee_id: Optional[int] = None,
#     letter_type: Optional[LetterType] = None,
#     letter_status: Optional[LetterStatus] = None,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     return HRLetterService.list_letters(
#         db,
#         employee_id=employee_id,
#         letter_type=letter_type,
#         status=letter_status,
#     )


# @router.get(
#     "/employee/{emp_id}",
#     response_model=List[HRLetterResponse],
#     summary="Get all letters for a specific employee",
# )
# def get_letters_by_employee(
#     emp_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin", "employee"])),
# ):
#     """
#     Employees can only fetch their own letters.
#     HR Admins can fetch any employee's letters.
#     """
#     if current_user.role == "employee" and current_user.id != emp_id:
#         raise HTTPException(status_code=403, detail="Access denied")
#     return HRLetterService.list_letters(db, employee_id=emp_id)


# @router.get(
#     "/{letter_id}",
#     response_model=HRLetterResponse,
#     summary="Get a specific issued letter",
# )
# def get_letter(
#     letter_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user),
# ):
#     letter = HRLetterService.get_letter(db, letter_id)
#     if not letter:
#         raise HTTPException(status_code=404, detail="Letter not found")
#     if current_user.role == "employee" and letter.employee_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Access denied")
#     return letter


# @router.patch(
#     "/{letter_id}/status",
#     response_model=HRLetterResponse,
#     summary="Update letter status (issue / revoke)",
# )
# def update_letter_status(
#     letter_id: int,
#     payload: HRLetterStatusUpdate,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     return HRLetterService.update_letter_status(db, letter_id, payload, current_user.id)


# @router.post(
#     "/{letter_id}/send-email",
#     status_code=status.HTTP_200_OK,
#     summary="Email the letter PDF to the employee",
# )
# def send_letter_email(
#     letter_id: int,
#     payload: SendLetterEmailRequest,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
#     current_user=Depends(require_roles(["hr_admin", "superadmin"])),
# ):
#     """
#     Sends the issued letter PDF to the employee via email.
#     Marks letter status as sent.
#     """
#     background_tasks.add_task(
#         HRLetterService.send_email, db, letter_id, payload, current_user.id
#     )
#     return {"message": "Letter email queued for delivery."}


# @router.get(
#     "/{letter_id}/download",
#     summary="Download letter as PDF",
# )
# def download_letter_pdf(
#     letter_id: int,
#     db: Session = Depends(get_db),
#     current_user=Depends(get_current_user),
# ):
#     letter = HRLetterService.get_letter(db, letter_id)
#     if not letter:
#         raise HTTPException(status_code=404, detail="Letter not found")
#     if current_user.role == "employee" and letter.employee_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Access denied")
#     return HRLetterService.get_download_url(db, letter_id)
"""
Router: HR Letters — Complete
Prefix : /api/hr-letters
Covers : Templates + Issue/Send/Revoke + Workflow + Employee Portal + Reports + Settings
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlmodel import Session

from schema.HR_Operations.letter_generation import (
    HRLetterTemplateCreate, HRLetterTemplateUpdate, HRLetterTemplateResponse,
    HRLetterIssueRequest, HRLetterStatusUpdate, HRLetterResponse,
    SendLetterEmailRequest,
)
from schema.HR_Operations.letter_generation import (
    LetterSettingsUpdate, LetterSettingsResponse,
    LetterRequestCreate, LetterRequestApprove, LetterRequestReject,
    LetterRequestResponse,
    LetterUsageReportResponse, EmployeeWiseReportResponse,
)
from model.HR_Operations.letter_generation import LetterType, LetterStatus
from services.letters_service import (
    HRLetterService, LetterSettingsService,
    LetterWorkflowService, LetterReportsService,
)
from core.dependencies import get_db, get_current_user, require_roles

router = APIRouter(prefix="/api/hr-letters", tags=["HR Letters"])


# ═══════════════════════════════════════════════════════════════════════════════
#  LETTER TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/templates", response_model=HRLetterTemplateResponse,
    status_code=status.HTTP_201_CREATED, summary="Create HR letter template")
def create_template(payload: HRLetterTemplateCreate, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return HRLetterService.create_template(db, payload, current_user.id)


@router.get("/templates", response_model=List[HRLetterTemplateResponse],
    summary="List all active HR letter templates")
def list_templates(letter_type: Optional[LetterType] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "admin"]))):
    return HRLetterService.list_templates(db, letter_type=letter_type)


@router.get("/templates/{template_id}", response_model=HRLetterTemplateResponse,
    summary="Get a specific letter template")
def get_template(template_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "admin"]))):
    template = HRLetterService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=HRLetterTemplateResponse,
    summary="Update a letter template")
def update_template(template_id: int, payload: HRLetterTemplateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return HRLetterService.update_template(db, template_id, payload)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a letter template")
def delete_template(template_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    HRLetterService.delete_template(db, template_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/settings", response_model=LetterSettingsResponse,
    summary="Get HR Letter system settings")
def get_settings(db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return LetterSettingsService.get_settings(db)


@router.put("/settings", response_model=LetterSettingsResponse,
    summary="Update HR Letter system settings")
def update_settings(payload: LetterSettingsUpdate, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return LetterSettingsService.update_settings(db, payload, current_user.id)


@router.post("/settings/reset", response_model=LetterSettingsResponse,
    summary="Reset settings to default")
def reset_settings(db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return LetterSettingsService.reset_settings(db, current_user.id)


# ═══════════════════════════════════════════════════════════════════════════════
#  EMPLOYEE PORTAL — Self-Service Requests
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/requests", response_model=LetterRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Employee submits a new letter request")
def submit_letter_request(payload: LetterRequestCreate,
    db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return LetterWorkflowService.submit_request(db, payload, current_user.id)


@router.get("/requests/my", response_model=List[LetterRequestResponse],
    summary="Get my letter requests")
def get_my_requests(db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    return LetterWorkflowService.get_my_requests(db, current_user.id)


@router.get("/requests/employee/{emp_id}", response_model=List[LetterRequestResponse],
    summary="Get all letter requests for a specific employee")
def get_employee_requests(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "manager"]))):
    return LetterWorkflowService.get_my_requests(db, emp_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW — Approval Management
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/requests", response_model=List[LetterRequestResponse],
    summary="List all letter requests")
def list_all_requests(req_status: Optional[str] = None,
    priority: Optional[str] = None, letter_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "manager"]))):
    return LetterWorkflowService.get_all_requests(db, req_status, priority, letter_type)


@router.get("/requests/stats", summary="Workflow dashboard statistics")
def get_workflow_stats(db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "manager"]))):
    return LetterWorkflowService.get_workflow_stats(db)


@router.get("/requests/{request_id}", response_model=LetterRequestResponse,
    summary="Get a specific letter request")
def get_request(request_id: int, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    req = LetterWorkflowService.get_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role == "employee" and req.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return req


@router.patch("/requests/{request_id}/approve", response_model=LetterRequestResponse,
    summary="Approve a letter request")
def approve_request(request_id: int, payload: LetterRequestApprove,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["manager", "hr_admin", "superadmin"]))):
    return LetterWorkflowService.approve_request(
        db, request_id, payload, current_user.id, current_user.role)


@router.patch("/requests/{request_id}/reject", response_model=LetterRequestResponse,
    summary="Reject a letter request")
def reject_request(request_id: int, payload: LetterRequestReject,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["manager", "hr_admin", "superadmin"]))):
    return LetterWorkflowService.reject_request(db, request_id, payload, current_user.id)


@router.post("/requests/bulk-approve", summary="Bulk approve multiple letter requests")
def bulk_approve_requests(request_ids: List[int], db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return LetterWorkflowService.bulk_approve(
        db, request_ids, current_user.id, current_user.role)


# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUED LETTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/issue", response_model=HRLetterResponse,
    status_code=status.HTTP_201_CREATED, summary="Issue a letter to an employee")
def issue_letter(payload: HRLetterIssueRequest, background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    letter = HRLetterService.issue_letter(db, payload, current_user.id)
    background_tasks.add_task(HRLetterService.generate_pdf, db, letter.id)
    return letter


@router.get("/", response_model=List[HRLetterResponse],
    summary="List all issued letters")
def list_letters(employee_id: Optional[int] = None,
    letter_type: Optional[LetterType] = None,
    letter_status: Optional[LetterStatus] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return HRLetterService.list_letters(db, employee_id=employee_id,
        letter_type=letter_type, status=letter_status)


@router.get("/employee/{emp_id}", response_model=List[HRLetterResponse],
    summary="Get all letters for a specific employee")
def get_letters_by_employee(emp_id: int, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "employee"]))):
    if current_user.role == "employee" and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return HRLetterService.list_letters(db, employee_id=emp_id)


@router.patch("/{letter_id}/status", response_model=HRLetterResponse,
    summary="Update letter status")
def update_letter_status(letter_id: int, payload: HRLetterStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return HRLetterService.update_letter_status(db, letter_id, payload, current_user.id)


@router.post("/{letter_id}/send-email", status_code=status.HTTP_200_OK,
    summary="Email the letter PDF to the employee")
def send_letter_email(letter_id: int, payload: SendLetterEmailRequest,
    background_tasks: BackgroundTasks, db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    background_tasks.add_task(
        HRLetterService.send_email, db, letter_id, payload, current_user.id)
    return {"message": "Letter email queued for delivery."}


@router.get("/{letter_id}/download", summary="Download letter as PDF")
def download_letter_pdf(letter_id: int, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    letter = HRLetterService.get_letter(db, letter_id)
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")
    if current_user.role == "employee" and letter.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return HRLetterService.get_download_url(db, letter_id)


@router.get("/{letter_id}", response_model=HRLetterResponse,
    summary="Get a specific issued letter")
def get_letter(letter_id: int, db: Session = Depends(get_db),
    current_user=Depends(get_current_user)):
    letter = HRLetterService.get_letter(db, letter_id)
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")
    if current_user.role == "employee" and letter.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return letter


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reports/usage", response_model=LetterUsageReportResponse,
    summary="Letter usage report")
def letter_usage_report(db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return LetterReportsService.get_letter_usage_report(db)


@router.get("/reports/employee-wise", response_model=EmployeeWiseReportResponse,
    summary="Employee-wise letter report")
def employee_wise_report(db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    return LetterReportsService.get_employee_wise_report(db)


@router.get("/reports/usage/pdf", summary="Download letter usage report as PDF")
def download_usage_report_pdf(
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    pdf_path = LetterReportsService.export_report_pdf("usage")
    return FileResponse(pdf_path, media_type="application/pdf",
        filename="letter_usage_report.pdf")


@router.get("/reports/employee-wise/pdf",
    summary="Download employee-wise report as PDF")
def download_employee_report_pdf(
    current_user=Depends(require_roles(["hr_admin", "superadmin"]))):
    pdf_path = LetterReportsService.export_report_pdf("employee_wise")
    return FileResponse(pdf_path, media_type="application/pdf",
        filename="employee_wise_report.pdf")