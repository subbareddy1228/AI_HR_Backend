# """
# Router: HR Letters
# Prefix : /api/hr-letters
# Covers : Templates CRUD + Issue / Send / Revoke letters + PDF generation
# """
 
# from typing import List, Optional
# from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
# from sqlalchemy.ext.asyncio import AsyncSession
 
# from schema.HR_Operations.letter_generation import (
#     HRLetterTemplateCreate, HRLetterTemplateUpdate, HRLetterTemplateResponse,
#     HRLetterIssueRequest, HRLetterStatusUpdate, HRLetterResponse,
#     SendLetterEmailRequest,
# )
# from model.HR_Operations.letter_generation import LetterType, LetterStatus
# from services.letters_service import HRLetterService
# from core.dependencies import get_db, get_current_user, require_roles
# from core.dependencies import Role
 
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
# async def create_template(
#     payload: HRLetterTemplateCreate,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     """
#     Create a reusable letter template.
#     Body uses Jinja2 syntax — e.g. `{{ employee_name }}`.
#     """
#     return await HRLetterService.create_template(db, payload, current_user.id)
 
 
# @router.get(
#     "/templates",
#     response_model=List[HRLetterTemplateResponse],
#     summary="List all active HR letter templates",
# )
# async def list_templates(
#     letter_type: Optional[LetterType] = None,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN, Role.ADMIN])),
# ):
#     return await HRLetterService.list_templates(db, letter_type=letter_type)
 
 
# @router.get(
#     "/templates/{template_id}",
#     response_model=HRLetterTemplateResponse,
#     summary="Get a specific letter template",
# )
# async def get_template(
#     template_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN, Role.ADMIN])),
# ):
#     template = await HRLetterService.get_template(db, template_id)
#     if not template:
#         raise HTTPException(status_code=404, detail="Template not found")
#     return template
 
 
# @router.put(
#     "/templates/{template_id}",
#     response_model=HRLetterTemplateResponse,
#     summary="Update a letter template",
# )
# async def update_template(
#     template_id: int,
#     payload: HRLetterTemplateUpdate,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     return await HRLetterService.update_template(db, template_id, payload)
 
 
# @router.delete(
#     "/templates/{template_id}",
#     status_code=status.HTTP_204_NO_CONTENT,
#     summary="Delete (soft-delete) a letter template",
# )
# async def delete_template(
#     template_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     await HRLetterService.delete_template(db, template_id)
 
 
# # ═══════════════════════════════════════════════════════════════════════════════
# #  ISSUED LETTERS
# # ═══════════════════════════════════════════════════════════════════════════════
 
# @router.post(
#     "/issue",
#     response_model=HRLetterResponse,
#     status_code=status.HTTP_201_CREATED,
#     summary="Issue a letter to an employee",
# )
# async def issue_letter(
#     payload: HRLetterIssueRequest,
#     background_tasks: BackgroundTasks,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     """
#     Issue (create a draft) of a letter for an employee.
#     If `template_id` is provided, variables are merged automatically.
#     Triggers async PDF generation in the background.
#     """
#     letter = await HRLetterService.issue_letter(db, payload, current_user.id)
#     background_tasks.add_task(HRLetterService.generate_pdf, db, letter.id)
#     return letter
 
 
# @router.get(
#     "/",
#     response_model=List[HRLetterResponse],
#     summary="List all issued letters (HR Admin)",
# )
# async def list_letters(
#     employee_id: Optional[int] = None,
#     letter_type: Optional[LetterType] = None,
#     status: Optional[LetterStatus] = None,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     return await HRLetterService.list_letters(
#         db,
#         employee_id=employee_id,
#         letter_type=letter_type,
#         status=status,
#     )
 
 
# @router.get(
#     "/employee/{emp_id}",
#     response_model=List[HRLetterResponse],
#     summary="Get all letters for a specific employee",
# )
# async def get_letters_by_employee(
#     emp_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN, Role.EMPLOYEE])),
# ):
#     """
#     Employees can only fetch their own letters.
#     HR Admins can fetch any employee's letters.
#     """
#     if current_user.role == Role.EMPLOYEE and current_user.id != emp_id:
#         raise HTTPException(status_code=403, detail="Access denied")
#     return await HRLetterService.list_letters(db, employee_id=emp_id)
 
 
# @router.get(
#     "/{letter_id}",
#     response_model=HRLetterResponse,
#     summary="Get a specific issued letter",
# )
# async def get_letter(
#     letter_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(get_current_user),
# ):
#     letter = await HRLetterService.get_letter(db, letter_id)
#     if not letter:
#         raise HTTPException(status_code=404, detail="Letter not found")
#     # Employees restricted to their own letters
#     if current_user.role == Role.EMPLOYEE and letter.employee_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Access denied")
#     return letter
 
 
# @router.patch(
#     "/{letter_id}/status",
#     response_model=HRLetterResponse,
#     summary="Update letter status (issue / revoke)",
# )
# async def update_letter_status(
#     letter_id: int,
#     payload: HRLetterStatusUpdate,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     return await HRLetterService.update_letter_status(db, letter_id, payload, current_user.id)
 
 
# @router.post(
#     "/{letter_id}/send-email",
#     status_code=status.HTTP_200_OK,
#     summary="Email the letter PDF to the employee",
# )
# async def send_letter_email(
#     letter_id: int,
#     payload: SendLetterEmailRequest,
#     background_tasks: BackgroundTasks,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(require_roles([Role.HR_ADMIN, Role.SUPERADMIN])),
# ):
#     """
#     Sends the issued letter PDF to the employee via email (SMTP/SendGrid).
#     Marks letter status as `sent`.
#     """
#     background_tasks.add_task(
#         HRLetterService.send_email, db, letter_id, payload, current_user.id
#     )
#     return {"message": "Letter email queued for delivery."}
 
 
# @router.get(
#     "/{letter_id}/download",
#     summary="Download letter as PDF (returns signed URL or streaming response)",
# )
# async def download_letter_pdf(
#     letter_id: int,
#     db: AsyncSession = Depends(get_db),
#     current_user=Depends(get_current_user),
# ):
#     letter = await HRLetterService.get_letter(db, letter_id)
#     if not letter:
#         raise HTTPException(status_code=404, detail="Letter not found")
#     if current_user.role == Role.EMPLOYEE and letter.employee_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Access denied")
#     return await HRLetterService.get_download_url(db, letter_id)
"""
Router: HR Letters
Prefix : /api/hr-letters
Covers : Templates CRUD + Issue / Send / Revoke letters + PDF generation
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session

from schema.HR_Operations.letter_generation import (
    HRLetterTemplateCreate, HRLetterTemplateUpdate, HRLetterTemplateResponse,
    HRLetterIssueRequest, HRLetterStatusUpdate, HRLetterResponse,
    SendLetterEmailRequest,
)
from model.HR_Operations.letter_generation import LetterType, LetterStatus
from services.letters_service import HRLetterService
from core.dependencies import get_db, get_current_user, require_roles

router = APIRouter(prefix="/api/hr-letters", tags=["HR Letters"])


# ═══════════════════════════════════════════════════════════════════════════════
#  LETTER TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/templates",
    response_model=HRLetterTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create HR letter template",
)
def create_template(
    payload: HRLetterTemplateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    """
    Create a reusable letter template.
    Body uses Jinja2 syntax — e.g. {{ employee_name }}.
    """
    return HRLetterService.create_template(db, payload, current_user.id)


@router.get(
    "/templates",
    response_model=List[HRLetterTemplateResponse],
    summary="List all active HR letter templates",
)
def list_templates(
    letter_type: Optional[LetterType] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "admin"])),
):
    return HRLetterService.list_templates(db, letter_type=letter_type)


@router.get(
    "/templates/{template_id}",
    response_model=HRLetterTemplateResponse,
    summary="Get a specific letter template",
)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "admin"])),
):
    template = HRLetterService.get_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put(
    "/templates/{template_id}",
    response_model=HRLetterTemplateResponse,
    summary="Update a letter template",
)
def update_template(
    template_id: int,
    payload: HRLetterTemplateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    return HRLetterService.update_template(db, template_id, payload)


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete (soft-delete) a letter template",
)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    HRLetterService.delete_template(db, template_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUED LETTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/issue",
    response_model=HRLetterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a letter to an employee",
)
def issue_letter(
    payload: HRLetterIssueRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    """
    Issue (create a draft) of a letter for an employee.
    If template_id is provided, variables are merged automatically.
    Triggers async PDF generation in the background.
    """
    letter = HRLetterService.issue_letter(db, payload, current_user.id)
    background_tasks.add_task(HRLetterService.generate_pdf, db, letter.id)
    return letter


@router.get(
    "/",
    response_model=List[HRLetterResponse],
    summary="List all issued letters (HR Admin)",
)
def list_letters(
    employee_id: Optional[int] = None,
    letter_type: Optional[LetterType] = None,
    letter_status: Optional[LetterStatus] = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    return HRLetterService.list_letters(
        db,
        employee_id=employee_id,
        letter_type=letter_type,
        status=letter_status,
    )


@router.get(
    "/employee/{emp_id}",
    response_model=List[HRLetterResponse],
    summary="Get all letters for a specific employee",
)
def get_letters_by_employee(
    emp_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin", "employee"])),
):
    """
    Employees can only fetch their own letters.
    HR Admins can fetch any employee's letters.
    """
    if current_user.role == "employee" and current_user.id != emp_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return HRLetterService.list_letters(db, employee_id=emp_id)


@router.get(
    "/{letter_id}",
    response_model=HRLetterResponse,
    summary="Get a specific issued letter",
)
def get_letter(
    letter_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    letter = HRLetterService.get_letter(db, letter_id)
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")
    if current_user.role == "employee" and letter.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return letter


@router.patch(
    "/{letter_id}/status",
    response_model=HRLetterResponse,
    summary="Update letter status (issue / revoke)",
)
def update_letter_status(
    letter_id: int,
    payload: HRLetterStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    return HRLetterService.update_letter_status(db, letter_id, payload, current_user.id)


@router.post(
    "/{letter_id}/send-email",
    status_code=status.HTTP_200_OK,
    summary="Email the letter PDF to the employee",
)
def send_letter_email(
    letter_id: int,
    payload: SendLetterEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["hr_admin", "superadmin"])),
):
    """
    Sends the issued letter PDF to the employee via email.
    Marks letter status as sent.
    """
    background_tasks.add_task(
        HRLetterService.send_email, db, letter_id, payload, current_user.id
    )
    return {"message": "Letter email queued for delivery."}


@router.get(
    "/{letter_id}/download",
    summary="Download letter as PDF",
)
def download_letter_pdf(
    letter_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    letter = HRLetterService.get_letter(db, letter_id)
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")
    if current_user.role == "employee" and letter.employee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return HRLetterService.get_download_url(db, letter_id)