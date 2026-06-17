"""
Service: HR Letters
Handles template CRUD, letter issuance, PDF generation, and email dispatch.
"""

import json
import os
from datetime import datetime, date
from typing import Optional, List

from jinja2 import Template
from sqlmodel import Session, select
from sqlalchemy import and_
from fastapi import HTTPException

from model.HR_Operations.letter_generation import (
    HRLetterTemplate, HRLetter, LetterType, LetterStatus,
)
from schema.HR_Operations.letter_generation import (
    HRLetterTemplateCreate, HRLetterTemplateUpdate,
    HRLetterIssueRequest, HRLetterStatusUpdate, SendLetterEmailRequest,
)


class HRLetterService:

    # ── Templates ────────────────────────────────────────────────────────────

    @staticmethod
    def create_template(
        db: Session,
        payload: HRLetterTemplateCreate,
        created_by: int,
    ) -> HRLetterTemplate:
        variables_json = json.dumps(payload.variables) if payload.variables else None
        template = HRLetterTemplate(
            name=payload.name,
            letter_type=payload.letter_type,
            subject=payload.subject,
            body_html=payload.body_html,
            variables=variables_json,
            created_by=created_by,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def list_templates(
        db: Session,
        letter_type: Optional[LetterType] = None,
    ) -> List[HRLetterTemplate]:
        query = select(HRLetterTemplate).where(
            HRLetterTemplate.is_deleted == False,
            HRLetterTemplate.is_active == True,
        )
        if letter_type:
            query = query.where(HRLetterTemplate.letter_type == letter_type)
        result = db.execute(query)
        return result.scalars().all()

    @staticmethod
    def get_template(db: Session, template_id: int) -> Optional[HRLetterTemplate]:
        result = db.execute(
            select(HRLetterTemplate).where(
                HRLetterTemplate.id == template_id,
                HRLetterTemplate.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def update_template(
        db: Session,
        template_id: int,
        payload: HRLetterTemplateUpdate,
    ) -> HRLetterTemplate:
        template = HRLetterService.get_template(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        for field, value in payload.dict(exclude_none=True).items():
            if field == "variables" and value is not None:
                value = json.dumps(value)
            setattr(template, field, value)
        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete_template(db: Session, template_id: int):
        template = HRLetterService.get_template(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        template.is_deleted = True
        template.updated_at = datetime.utcnow()
        db.commit()

    # ── Letter Issuance ──────────────────────────────────────────────────────

    @staticmethod
    def issue_letter(
        db: Session,
        payload: HRLetterIssueRequest,
        issued_by: int,
    ) -> HRLetter:
        body_html = payload.body_html
        if payload.template_id:
            tpl = HRLetterService.get_template(db, payload.template_id)
            if tpl:
                body_html = Template(tpl.body_html).render()

        letter = HRLetter(
            employee_id=payload.employee_id,
            template_id=payload.template_id,
            letter_type=payload.letter_type,
            subject=payload.subject,
            body_html=body_html,
            status=LetterStatus.DRAFT,
            issued_by=issued_by,
            issued_on=payload.issued_on or date.today(),
            notes=payload.notes,
        )
        db.add(letter)
        db.commit()
        db.refresh(letter)
        return letter

    @staticmethod
    def list_letters(
        db: Session,
        employee_id: Optional[int] = None,
        letter_type: Optional[LetterType] = None,
        status: Optional[LetterStatus] = None,
    ) -> List[HRLetter]:
        conditions = [HRLetter.is_deleted == False]
        if employee_id:
            conditions.append(HRLetter.employee_id == employee_id)
        if letter_type:
            conditions.append(HRLetter.letter_type == letter_type)
        if status:
            conditions.append(HRLetter.status == status)
        result = db.execute(select(HRLetter).where(and_(*conditions)))
        return result.scalars().all()

    @staticmethod
    def get_letter(db: Session, letter_id: int) -> Optional[HRLetter]:
        result = db.execute(
            select(HRLetter).where(
                HRLetter.id == letter_id,
                HRLetter.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def update_letter_status(
        db: Session,
        letter_id: int,
        payload: HRLetterStatusUpdate,
        updated_by: int,
    ) -> HRLetter:
        letter = HRLetterService.get_letter(db, letter_id)
        if not letter:
            raise HTTPException(status_code=404, detail="Letter not found")
        letter.status = payload.status
        if payload.status == LetterStatus.ISSUED:
            letter.issued_on = date.today()
        elif payload.status == LetterStatus.REVOKED:
            letter.revoked_at = datetime.utcnow()
            letter.revoke_reason = payload.revoke_reason
        letter.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(letter)
        return letter

    # ── PDF Generation ───────────────────────────────────────────────────────

    @staticmethod
    def generate_pdf(db: Session, letter_id: int):
        try:
            from fpdf import FPDF
            letter = HRLetterService.get_letter(db, letter_id)
            if not letter:
                return
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=letter.subject, ln=True, align="C")
            pdf.multi_cell(0, 10, txt="Please refer to the official document.")
            output_dir = os.path.join("uploads", "hr_letters")
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"letter_{letter_id}.pdf")
            pdf.output(pdf_path)
            letter.pdf_path = pdf_path
            letter.updated_at = datetime.utcnow()
            db.commit()
        except Exception:
            pass

    # ── Email Dispatch ───────────────────────────────────────────────────────

    @staticmethod
    def send_email(
        db: Session,
        letter_id: int,
        payload: SendLetterEmailRequest,
        sent_by: int,
    ):
        letter = HRLetterService.get_letter(db, letter_id)
        if not letter or not letter.pdf_path:
            return
        # TODO: integrate SMTP/SendGrid here
        letter.status = LetterStatus.SENT
        letter.sent_at = datetime.utcnow()
        letter.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def get_download_url(db: Session, letter_id: int) -> dict:
        letter = HRLetterService.get_letter(db, letter_id)
        if not letter or not letter.pdf_path:
            raise HTTPException(status_code=404, detail="PDF not yet generated")
        return {"download_url": f"/uploads/{letter.pdf_path}", "expires_in": 3600}
"""
Service: HR Letters
Handles template CRUD, letter issuance, PDF generation, and email dispatch.
"""

import json
import os
from datetime import datetime, date
from typing import Optional, List

from jinja2 import Template
from sqlmodel import Session, select
from sqlalchemy import and_
from fastapi import HTTPException

from model.HR_Operations.letter_generation import (
    HRLetterTemplate, HRLetter, LetterType, LetterStatus,
)
from schema.HR_Operations.letter_generation import (
    HRLetterTemplateCreate, HRLetterTemplateUpdate,
    HRLetterIssueRequest, HRLetterStatusUpdate, SendLetterEmailRequest,
)


class HRLetterService:

    # ── Templates ────────────────────────────────────────────────────────────

    @staticmethod
    def create_template(
        db: Session,
        payload: HRLetterTemplateCreate,
        created_by: int,
    ) -> HRLetterTemplate:
        variables_json = json.dumps(payload.variables) if payload.variables else None
        template = HRLetterTemplate(
            name=payload.name,
            letter_type=payload.letter_type,
            subject=payload.subject,
            body_html=payload.body_html,
            variables=variables_json,
            created_by=created_by,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def list_templates(
        db: Session,
        letter_type: Optional[LetterType] = None,
    ) -> List[HRLetterTemplate]:
        query = select(HRLetterTemplate).where(
            HRLetterTemplate.is_deleted == False,
            HRLetterTemplate.is_active == True,
        )
        if letter_type:
            query = query.where(HRLetterTemplate.letter_type == letter_type)
        result = db.execute(query)
        return result.scalars().all()

    @staticmethod
    def get_template(db: Session, template_id: int) -> Optional[HRLetterTemplate]:
        result = db.execute(
            select(HRLetterTemplate).where(
                HRLetterTemplate.id == template_id,
                HRLetterTemplate.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def update_template(
        db: Session,
        template_id: int,
        payload: HRLetterTemplateUpdate,
    ) -> HRLetterTemplate:
        template = HRLetterService.get_template(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        for field, value in payload.dict(exclude_none=True).items():
            if field == "variables" and value is not None:
                value = json.dumps(value)
            setattr(template, field, value)
        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete_template(db: Session, template_id: int):
        template = HRLetterService.get_template(db, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        template.is_deleted = True
        template.updated_at = datetime.utcnow()
        db.commit()

    # ── Letter Issuance ──────────────────────────────────────────────────────

    @staticmethod
    def issue_letter(
        db: Session,
        payload: HRLetterIssueRequest,
        issued_by: int,
    ) -> HRLetter:
        body_html = payload.body_html
        if payload.template_id:
            tpl = HRLetterService.get_template(db, payload.template_id)
            if tpl:
                body_html = Template(tpl.body_html).render()

        letter = HRLetter(
            employee_id=payload.employee_id,
            template_id=payload.template_id,
            letter_type=payload.letter_type,
            subject=payload.subject,
            body_html=body_html,
            status=LetterStatus.DRAFT,
            issued_by=issued_by,
            issued_on=payload.issued_on or date.today(),
            notes=payload.notes,
        )
        db.add(letter)
        db.commit()
        db.refresh(letter)
        return letter

    @staticmethod
    def list_letters(
        db: Session,
        employee_id: Optional[int] = None,
        letter_type: Optional[LetterType] = None,
        status: Optional[LetterStatus] = None,
    ) -> List[HRLetter]:
        conditions = [HRLetter.is_deleted == False]
        if employee_id:
            conditions.append(HRLetter.employee_id == employee_id)
        if letter_type:
            conditions.append(HRLetter.letter_type == letter_type)
        if status:
            conditions.append(HRLetter.status == status)
        result = db.execute(select(HRLetter).where(and_(*conditions)))
        return result.scalars().all()

    @staticmethod
    def get_letter(db: Session, letter_id: int) -> Optional[HRLetter]:
        result = db.execute(
            select(HRLetter).where(
                HRLetter.id == letter_id,
                HRLetter.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def update_letter_status(
        db: Session,
        letter_id: int,
        payload: HRLetterStatusUpdate,
        updated_by: int,
    ) -> HRLetter:
        letter = HRLetterService.get_letter(db, letter_id)
        if not letter:
            raise HTTPException(status_code=404, detail="Letter not found")
        letter.status = payload.status
        if payload.status == LetterStatus.ISSUED:
            letter.issued_on = date.today()
        elif payload.status == LetterStatus.REVOKED:
            letter.revoked_at = datetime.utcnow()
            letter.revoke_reason = payload.revoke_reason
        letter.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(letter)
        return letter

    # ── PDF Generation ───────────────────────────────────────────────────────

    @staticmethod
    def generate_pdf(db: Session, letter_id: int):
        try:
            from fpdf import FPDF
            letter = HRLetterService.get_letter(db, letter_id)
            if not letter:
                return
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=letter.subject, ln=True, align="C")
            pdf.multi_cell(0, 10, txt="Please refer to the official document.")
            output_dir = os.path.join("uploads", "hr_letters")
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"letter_{letter_id}.pdf")
            pdf.output(pdf_path)
            letter.pdf_path = pdf_path
            letter.updated_at = datetime.utcnow()
            db.commit()
        except Exception:
            pass

    # ── Email Dispatch ───────────────────────────────────────────────────────

    @staticmethod
    def send_email(
        db: Session,
        letter_id: int,
        payload: SendLetterEmailRequest,
        sent_by: int,
    ):
        letter = HRLetterService.get_letter(db, letter_id)
        if not letter or not letter.pdf_path:
            return
        # TODO: integrate SMTP/SendGrid here
        letter.status = LetterStatus.SENT
        letter.sent_at = datetime.utcnow()
        letter.updated_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def get_download_url(db: Session, letter_id: int) -> dict:
        letter = HRLetterService.get_letter(db, letter_id)
        if not letter or not letter.pdf_path:
            raise HTTPException(status_code=404, detail="PDF not yet generated")
        return {"download_url": f"/uploads/{letter.pdf_path}", "expires_in": 3600}


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

from model.HR_Operations.letter_generation import LetterSettings, LetterRequest, LetterApprovalStep
from schema.HR_Operations.letter_generation import (
    LetterSettingsUpdate, LetterRequestCreate,
    LetterRequestApprove, LetterRequestReject,
    LetterUsageReportResponse, EmployeeWiseReportResponse,
)


class LetterSettingsService:

    @staticmethod
    def get_settings(db: Session) -> LetterSettings:
        result = db.execute(select(LetterSettings).limit(1))
        settings = result.scalar_one_or_none()
        if not settings:
            settings = LetterSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    def update_settings(db: Session, payload: LetterSettingsUpdate, updated_by: int) -> LetterSettings:
        settings = LetterSettingsService.get_settings(db)
        for field, value in payload.dict(exclude_none=True).items():
            setattr(settings, field, value)
        settings.updated_by = updated_by
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def reset_settings(db: Session, updated_by: int) -> LetterSettings:
        settings = LetterSettingsService.get_settings(db)
        defaults = LetterSettings()
        for field in ["auto_approve_salary_certificate", "auto_approve_experience_certificate",
                      "default_letter_format", "audit_trail_retention_days",
                      "email_new_requests", "email_approvals", "email_downloads",
                      "default_workflow_sla_hours", "high_priority_sla_hours",
                      "medium_priority_sla_hours", "low_priority_sla_hours",
                      "default_digital_signature"]:
            setattr(settings, field, getattr(defaults, field))
        settings.updated_by = updated_by
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings


# ═══════════════════════════════════════════════════════════════════════════════
#  WORKFLOW SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class LetterWorkflowService:

    @staticmethod
    def submit_request(db: Session, payload: LetterRequestCreate, employee_id: int) -> LetterRequest:
        settings = LetterSettingsService.get_settings(db)
        auto_approve = (
            (payload.letter_type == "salary_certificate" and settings.auto_approve_salary_certificate)
            or (payload.letter_type == "experience" and settings.auto_approve_experience_certificate)
        )
        count = len(db.execute(select(LetterRequest)).scalars().all())
        request_id = f"LTR-REQ-{datetime.utcnow().year}-{count + 1:03d}"

        request = LetterRequest(
            request_id=request_id,
            employee_id=employee_id,
            letter_type=payload.letter_type,
            purpose=payload.purpose,
            priority=payload.priority,
            notes=payload.notes,
            requested_by=employee_id,
            status="approved" if auto_approve else "pending",
            approved_by=0 if auto_approve else None,
            approved_at=datetime.utcnow() if auto_approve else None,
        )
        db.add(request)
        db.flush()

        if not auto_approve:
            for i, role in enumerate(["manager", "hr", "hr_admin"], start=1):
                step = LetterApprovalStep(
                    request_id=request.id,
                    step_order=i,
                    approver_role=role,
                    status="pending" if i == 1 else "waiting",
                )
                db.add(step)

        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def get_my_requests(db: Session, employee_id: int) -> list:
        result = db.execute(
            select(LetterRequest).where(
                LetterRequest.employee_id == employee_id,
                LetterRequest.is_deleted == False,
            ).order_by(LetterRequest.requested_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    def get_all_requests(db: Session, status=None, priority=None, letter_type=None) -> list:
        query = select(LetterRequest).where(LetterRequest.is_deleted == False)
        if status:
            query = query.where(LetterRequest.status == status)
        if priority:
            query = query.where(LetterRequest.priority == priority)
        if letter_type:
            query = query.where(LetterRequest.letter_type == letter_type)
        return db.execute(query.order_by(LetterRequest.requested_at.desc())).scalars().all()

    @staticmethod
    def get_request(db: Session, request_id: int):
        return db.get(LetterRequest, request_id)

    @staticmethod
    def approve_request(db: Session, request_id: int, payload: LetterRequestApprove,
                        approver_id: int, approver_role: str) -> LetterRequest:
        request = db.get(LetterRequest, request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        if request.status not in ("pending", "in_review"):
            raise HTTPException(status_code=400, detail=f"Cannot approve: {request.status}")

        steps = db.execute(
            select(LetterApprovalStep).where(
                LetterApprovalStep.request_id == request_id,
                LetterApprovalStep.status == "pending",
            ).order_by(LetterApprovalStep.step_order)
        ).scalars().all()

        if steps:
            steps[0].status = "approved"
            steps[0].approver_id = approver_id
            steps[0].actioned_at = datetime.utcnow()
            steps[0].remarks = payload.remarks
            remaining = steps[1:]
            if remaining:
                remaining[0].status = "pending"
                request.status = "in_review"
            else:
                request.status = "approved"
                request.approved_by = approver_id
                request.approved_at = datetime.utcnow()
        else:
            request.status = "approved"
            request.approved_by = approver_id
            request.approved_at = datetime.utcnow()

        request.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def reject_request(db: Session, request_id: int, payload: LetterRequestReject,
                       rejector_id: int) -> LetterRequest:
        request = db.get(LetterRequest, request_id)
        if not request:
            raise HTTPException(status_code=404, detail="Request not found")
        request.status = "rejected"
        request.rejected_by = rejector_id
        request.rejected_at = datetime.utcnow()
        request.reject_reason = payload.reject_reason
        request.updated_at = datetime.utcnow()
        steps = db.execute(
            select(LetterApprovalStep).where(LetterApprovalStep.request_id == request_id)
        ).scalars().all()
        for step in steps:
            if step.status in ("pending", "waiting"):
                step.status = "rejected"
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def bulk_approve(db: Session, request_ids: list, approver_id: int, approver_role: str) -> dict:
        approved, failed = [], []
        for rid in request_ids:
            try:
                LetterWorkflowService.approve_request(
                    db, rid, LetterRequestApprove(), approver_id, approver_role)
                approved.append(rid)
            except Exception as e:
                failed.append({"id": rid, "error": str(e)})
        return {"approved": approved, "failed": failed}

    @staticmethod
    def get_workflow_stats(db: Session) -> dict:
        all_r = db.execute(select(LetterRequest).where(LetterRequest.is_deleted == False)).scalars().all()
        return {
            "total": len(all_r),
            "pending": sum(1 for r in all_r if r.status == "pending"),
            "in_review": sum(1 for r in all_r if r.status == "in_review"),
            "approved": sum(1 for r in all_r if r.status == "approved"),
            "rejected": sum(1 for r in all_r if r.status == "rejected"),
            "generated": sum(1 for r in all_r if r.status == "generated"),
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  REPORTS SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

class LetterReportsService:

    @staticmethod
    def get_letter_usage_report(db: Session) -> LetterUsageReportResponse:
        all_r = db.execute(select(LetterRequest).where(LetterRequest.is_deleted == False)).scalars().all()
        total = len(all_r)
        approved = sum(1 for r in all_r if r.status in ("approved", "generated"))
        pending = sum(1 for r in all_r if r.status in ("pending", "in_review"))
        rejected = sum(1 for r in all_r if r.status == "rejected")

        type_counts: dict = {}
        for r in all_r:
            type_counts[r.letter_type] = type_counts.get(r.letter_type, 0) + 1
        template_usage = sorted([{"letter_type": k, "count": v} for k, v in type_counts.items()],
                                 key=lambda x: -x["count"])

        monthly: dict = {}
        for r in all_r:
            month = r.requested_at.strftime("%Y-%m")
            monthly[month] = monthly.get(month, 0) + 1
        monthly_trends = [{"month": k, "count": v} for k, v in sorted(monthly.items())]

        return LetterUsageReportResponse(
            total_requests=total, approved=approved, pending=pending, rejected=rejected,
            template_usage=template_usage, monthly_trends=monthly_trends,
            approval_rate_pct=round(approved / total * 100, 1) if total else 0,
            download_frequency=[],
        )

    @staticmethod
    def get_employee_wise_report(db: Session) -> EmployeeWiseReportResponse:
        all_r = db.execute(select(LetterRequest).where(LetterRequest.is_deleted == False)).scalars().all()
        emp_map: dict = {}
        for r in all_r:
            eid = r.employee_id
            if eid not in emp_map:
                emp_map[eid] = {"employee_id": eid, "total": 0, "approved": 0, "pending": 0}
            emp_map[eid]["total"] += 1
            if r.status in ("approved", "generated"):
                emp_map[eid]["approved"] += 1
            if r.status in ("pending", "in_review"):
                emp_map[eid]["pending"] += 1

        type_counts: dict = {}
        for r in all_r:
            type_counts[r.letter_type] = type_counts.get(r.letter_type, 0) + 1

        return EmployeeWiseReportResponse(
            total_active_employees=len(emp_map),
            pending_requests=sum(1 for r in all_r if r.status in ("pending", "in_review")),
            employee_data=list(emp_map.values()),
            most_requested_letter_types=sorted(
                [{"letter_type": k, "count": v} for k, v in type_counts.items()],
                key=lambda x: -x["count"])[:5],
            department_wise=[],
        )

    @staticmethod
    def export_report_pdf(report_type: str) -> str:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"HR Letter {report_type.title()} Report", ln=True, align="C")
            pdf.cell(200, 10, txt=f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}", ln=True)
            output_dir = os.path.join("uploads", "reports")
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"report_{report_type}_{datetime.utcnow().strftime('%Y%m%d')}.pdf")
            pdf.output(pdf_path)
            return pdf_path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")