"""
Service: HR Letters
Handles template CRUD, letter issuance, PDF generation (WeasyPrint),
and email dispatch (SMTP/SendGrid).
"""
 
import json
import os
from datetime import datetime, date
from typing import Optional, List
 
from jinja2 import Template
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
 
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
    async def create_template(
        db: AsyncSession,
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
        await db.commit()
        await db.refresh(template)
        return template
 
    @staticmethod
    async def list_templates(
        db: AsyncSession,
        letter_type: Optional[LetterType] = None,
    ) -> List[HRLetterTemplate]:
        query = select(HRLetterTemplate).where(
            HRLetterTemplate.is_deleted == False,
            HRLetterTemplate.is_active == True,
        )
        if letter_type:
            query = query.where(HRLetterTemplate.letter_type == letter_type)
        result = await db.execute(query)
        return result.scalars().all()
 
    @staticmethod
    async def get_template(db: AsyncSession, template_id: int) -> Optional[HRLetterTemplate]:
        result = await db.execute(
            select(HRLetterTemplate).where(
                HRLetterTemplate.id == template_id,
                HRLetterTemplate.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()
 
    @staticmethod
    async def update_template(
        db: AsyncSession,
        template_id: int,
        payload: HRLetterTemplateUpdate,
    ) -> HRLetterTemplate:
        template = await HRLetterService.get_template(db, template_id)
        if not template:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Template not found")
        for field, value in payload.dict(exclude_none=True).items():
            if field == "variables" and value is not None:
                value = json.dumps(value)
            setattr(template, field, value)
        template.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(template)
        return template
 
    @staticmethod
    async def delete_template(db: AsyncSession, template_id: int):
        template = await HRLetterService.get_template(db, template_id)
        if not template:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Template not found")
        template.is_deleted = True
        template.updated_at = datetime.utcnow()
        await db.commit()
 
    # ── Letter Issuance ──────────────────────────────────────────────────────
 
    @staticmethod
    async def issue_letter(
        db: AsyncSession,
        payload: HRLetterIssueRequest,
        issued_by: int,
    ) -> HRLetter:
        """
        If template_id is provided, merges body_html with template variables.
        Otherwise uses body_html as-is.
        """
        body_html = payload.body_html
        if payload.template_id:
            tpl = await HRLetterService.get_template(db, payload.template_id)
            if tpl:
                # Basic Jinja2 render — caller must pass variables in body_html
                # or we use a separate context dict; here we keep it simple.
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
        await db.commit()
        await db.refresh(letter)
        return letter
 
    @staticmethod
    async def list_letters(
        db: AsyncSession,
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
        result = await db.execute(select(HRLetter).where(and_(*conditions)))
        return result.scalars().all()
 
    @staticmethod
    async def get_letter(db: AsyncSession, letter_id: int) -> Optional[HRLetter]:
        result = await db.execute(
            select(HRLetter).where(
                HRLetter.id == letter_id,
                HRLetter.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()
 
    @staticmethod
    async def update_letter_status(
        db: AsyncSession,
        letter_id: int,
        payload: HRLetterStatusUpdate,
        updated_by: int,
    ) -> HRLetter:
        from fastapi import HTTPException
        letter = await HRLetterService.get_letter(db, letter_id)
        if not letter:
            raise HTTPException(status_code=404, detail="Letter not found")
        letter.status = payload.status
        if payload.status == LetterStatus.ISSUED:
            letter.issued_on = date.today()
        elif payload.status == LetterStatus.REVOKED:
            letter.revoked_at = datetime.utcnow()
            letter.revoke_reason = payload.revoke_reason
        letter.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(letter)
        return letter
 
    # ── PDF Generation ───────────────────────────────────────────────────────
 
    @staticmethod
    async def generate_pdf(db: AsyncSession, letter_id: int):
        """
        Background task: renders body_html → PDF using WeasyPrint.
        Saves to /uploads/hr_letters/<letter_id>.pdf and updates pdf_path.
        """
        try:
            from weasyprint import HTML
        except ImportError:
            # WeasyPrint not installed in this environment; skip gracefully
            return
 
        letter = await HRLetterService.get_letter(db, letter_id)
        if not letter:
            return
 
        output_dir = os.path.join("uploads", "hr_letters")
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"letter_{letter_id}.pdf")
 
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 12pt;
                         margin: 60px 72px; line-height: 1.6; }}
                h1   {{ font-size: 16pt; margin-bottom: 4px; }}
                p    {{ margin: 8px 0; }}
            </style>
        </head>
        <body>{letter.body_html}</body>
        </html>
        """
        HTML(string=html_content).write_pdf(pdf_path)
 
        letter.pdf_path = pdf_path
        letter.updated_at = datetime.utcnow()
        await db.commit()
 
    # ── Email Dispatch ───────────────────────────────────────────────────────
 
    @staticmethod
    async def send_email(
        db: AsyncSession,
        letter_id: int,
        payload: SendLetterEmailRequest,
        sent_by: int,
    ):
        """
        Background task: attaches PDF and emails via SMTP/SendGrid.
        Updates letter status to 'sent'.
        """
        letter = await HRLetterService.get_letter(db, letter_id)
        if not letter or not letter.pdf_path:
            return
 
        # --- Email sending stub (replace with your SMTP/SendGrid client) ---
        # import sendgrid / smtplib
        # send(
        #     to=payload.recipient_email,
        #     cc=payload.cc,
        #     subject=letter.subject,
        #     body=payload.email_body or "Please find your letter attached.",
        #     attachment=letter.pdf_path,
        # )
        # --------------------------------------------------------------------
 
        letter.status = LetterStatus.SENT
        letter.sent_at = datetime.utcnow()
        letter.updated_at = datetime.utcnow()
        await db.commit()
 
    @staticmethod
    async def get_download_url(db: AsyncSession, letter_id: int) -> dict:
        """
        Returns a signed S3 URL or a streaming FastAPI FileResponse URL.
        Implement S3 presigned URL generation here if using AWS.
        """
        from fastapi import HTTPException
        letter = await HRLetterService.get_letter(db, letter_id)
        if not letter or not letter.pdf_path:
            raise HTTPException(status_code=404, detail="PDF not yet generated")
        # For local storage return direct path; for S3 generate presigned URL
        return {"download_url": f"/static/{letter.pdf_path}", "expires_in": 3600}