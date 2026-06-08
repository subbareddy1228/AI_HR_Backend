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