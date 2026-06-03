"""
Service: Employee Separation & Exit Management
Handles resignation workflow, clearance, exit interviews (+ AI sentiment),
FnF settlement computation, and separation letter generation.
"""

import json
import os
from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from model.HR_Operations.letter_generation import (
    Resignation, ResignationStatus,
    ClearanceChecklist, ClearanceItem, ClearanceStatus, ClearanceDepartment,
    ExitInterview,
    FnFSettlement, SettlementStatus,
    LetterType,
)
from schema.HR_Operations.letter_generation import (
    ResignationCreate, ResignationAccept,
    ClearanceInitiateRequest, ClearanceItemUpdate,
    ExitInterviewSubmit,
    FnFCalculateRequest,
    ExitAnalyticsResponse,
)

# Default clearance tasks seeded for every offboarding
DEFAULT_CLEARANCE_TASKS = [
    {"department": ClearanceDepartment.IT,      "task_description": "Return laptop, access cards, and peripherals"},
    {"department": ClearanceDepartment.IT,      "task_description": "Revoke system / application access"},
    {"department": ClearanceDepartment.FINANCE, "task_description": "Clear pending expense claims and advances"},
    {"department": ClearanceDepartment.FINANCE, "task_description": "Confirm no outstanding dues or liabilities"},
    {"department": ClearanceDepartment.ADMIN,   "task_description": "Return company ID card and office keys"},
    {"department": ClearanceDepartment.ADMIN,   "task_description": "Vacate assigned desk / locker"},
    {"department": ClearanceDepartment.HR,      "task_description": "Complete exit interview"},
    {"department": ClearanceDepartment.HR,      "task_description": "Submit pending timesheets and reports"},
]


class ExitService:

    # ── Resignation ──────────────────────────────────────────────────────────

    @staticmethod
    async def submit_resignation(
        db: AsyncSession,
        payload: ResignationCreate,
        employee_id: int,
    ) -> Resignation:
        from fastapi import HTTPException
        # Guard: one active resignation at a time
        existing = await ExitService.get_resignation(db, employee_id)
        if existing and existing.status == ResignationStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="A pending resignation already exists for this employee.",
            )
        resignation = Resignation(
            employee_id=employee_id,
            resignation_date=payload.resignation_date,
            reason=payload.reason,
            status=ResignationStatus.PENDING,
        )
        db.add(resignation)
        await db.commit()
        await db.refresh(resignation)
        # TODO: send notification email to HR + manager
        return resignation

    @staticmethod
    async def get_resignation(
        db: AsyncSession,
        employee_id: int,
    ) -> Optional[Resignation]:
        result = await db.execute(
            select(Resignation)
            .where(
                Resignation.employee_id == employee_id,
                Resignation.is_deleted == False,
            )
            .order_by(Resignation.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def accept_resignation(
        db: AsyncSession,
        resignation_id: int,
        payload: ResignationAccept,
        hr_user_id: int,
    ) -> Resignation:
        from fastapi import HTTPException
        resignation = await db.get(Resignation, resignation_id)
        if not resignation:
            raise HTTPException(status_code=404, detail="Resignation not found")
        if resignation.status != ResignationStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot accept resignation with status: {resignation.status}",
            )
        notice_days = (payload.last_working_day - date.today()).days
        resignation.status = ResignationStatus.ACCEPTED
        resignation.last_working_day = payload.last_working_day
        resignation.notice_period_days = notice_days
        resignation.accepted_by = hr_user_id
        resignation.accepted_at = datetime.utcnow()
        resignation.hr_remarks = payload.hr_remarks
        resignation.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(resignation)
        # TODO: send acceptance email to employee
        return resignation

    @staticmethod
    async def revoke_resignation(
        db: AsyncSession,
        resignation_id: int,
        employee_id: int,
    ) -> Resignation:
        from fastapi import HTTPException
        resignation = await db.get(Resignation, resignation_id)
        if not resignation:
            raise HTTPException(status_code=404, detail="Resignation not found")
        if resignation.employee_id != employee_id:
            raise HTTPException(status_code=403, detail="Access denied")
        if resignation.status == ResignationStatus.ACCEPTED:
            raise HTTPException(
                status_code=400,
                detail="Cannot revoke an already accepted resignation. Contact HR.",
            )
        resignation.status = ResignationStatus.REVOKED
        resignation.revoked_at = datetime.utcnow()
        resignation.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(resignation)
        return resignation

    @staticmethod
    async def get_notice_period_status(db: AsyncSession, employee_id: int) -> dict:
        from fastapi import HTTPException
        resignation = await ExitService.get_resignation(db, employee_id)
        if not resignation or resignation.status != ResignationStatus.ACCEPTED:
            raise HTTPException(status_code=404, detail="No accepted resignation found")
        today = date.today()
        days_served = (today - resignation.resignation_date).days
        days_remaining = max(
            0, (resignation.last_working_day - today).days
        ) if resignation.last_working_day else 0

        # Simple buyout: remaining_days * (monthly_salary / 30)
        # Replace with actual salary lookup in production
        return {
            "employee_id": employee_id,
            "resignation_date": resignation.resignation_date,
            "last_working_day": resignation.last_working_day,
            "notice_period_days": resignation.notice_period_days,
            "days_served": days_served,
            "days_remaining": days_remaining,
            "notice_served_pct": round(
                (days_served / resignation.notice_period_days * 100)
                if resignation.notice_period_days else 100,
                2,
            ),
        }

    # ── Clearance ────────────────────────────────────────────────────────────

    @staticmethod
    async def initiate_clearance(
        db: AsyncSession,
        employee_id: int,
        payload: ClearanceInitiateRequest,
        hr_user_id: int,
    ) -> ClearanceChecklist:
        checklist = ClearanceChecklist(
            employee_id=employee_id,
            resignation_id=payload.resignation_id,
            overall_status=ClearanceStatus.IN_PROGRESS,
            initiated_by=hr_user_id,
        )
        db.add(checklist)
        await db.flush()  # get checklist.id before adding items

        tasks = payload.custom_tasks if payload.custom_tasks else DEFAULT_CLEARANCE_TASKS
        for task in tasks:
            item = ClearanceItem(
                checklist_id=checklist.id,
                department=task["department"],
                task_description=task["task_description"],
            )
            db.add(item)

        await db.commit()
        await db.refresh(checklist)
        return checklist

    @staticmethod
    async def get_clearance(db: AsyncSession, employee_id: int) -> Optional[ClearanceChecklist]:
        result = await db.execute(
            select(ClearanceChecklist)
            .where(ClearanceChecklist.employee_id == employee_id)
            .order_by(ClearanceChecklist.initiated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def complete_clearance_item(
        db: AsyncSession,
        checklist_item_id: int,
        payload: ClearanceItemUpdate,
        completed_by: int,
    ) -> ClearanceChecklist:
        from fastapi import HTTPException
        item = await db.get(ClearanceItem, checklist_item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        item.is_completed = True
        item.completed_by = completed_by
        item.completed_at = datetime.utcnow()
        item.remarks = payload.remarks

        # Check if all items in this checklist are done
        checklist = await db.get(ClearanceChecklist, item.checklist_id)
        pending_result = await db.execute(
            select(func.count(ClearanceItem.id)).where(
                ClearanceItem.checklist_id == item.checklist_id,
                ClearanceItem.is_completed == False,
                ClearanceItem.id != checklist_item_id,
            )
        )
        remaining = pending_result.scalar()
        if remaining == 0:
            checklist.overall_status = ClearanceStatus.COMPLETED
            checklist.completed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(checklist)
        return checklist

    # ── Exit Interview ───────────────────────────────────────────────────────

    @staticmethod
    async def submit_exit_interview(
        db: AsyncSession,
        payload: ExitInterviewSubmit,
        employee_id: int,
    ) -> ExitInterview:
        interview = ExitInterview(
            employee_id=employee_id,
            resignation_id=payload.resignation_id,
            reason_for_leaving=payload.reason_for_leaving,
            job_satisfaction_score=payload.job_satisfaction_score,
            management_score=payload.management_score,
            work_environment_score=payload.work_environment_score,
            growth_opportunity_score=payload.growth_opportunity_score,
            would_rejoin=payload.would_rejoin,
            suggestions=payload.suggestions,
            additional_comments=payload.additional_comments,
        )
        db.add(interview)
        await db.commit()
        await db.refresh(interview)
        return interview

    @staticmethod
    async def run_sentiment_analysis(db: AsyncSession, interview_id: int):
        """
        Background task: calls OpenAI GPT-4 to analyse exit interview sentiment.
        Updates sentiment_label, sentiment_score, and ai_summary on the record.
        """
        import httpx, os

        interview = await db.get(ExitInterview, interview_id)
        if not interview:
            return

        combined_text = " ".join(filter(None, [
            interview.reason_for_leaving,
            interview.suggestions,
            interview.additional_comments,
        ]))
        if not combined_text.strip():
            return

        prompt = (
            "You are an HR analytics assistant. Analyse the following employee exit "
            "interview response and return a JSON object with keys: "
            "'sentiment' (one of: positive/neutral/negative), "
            "'score' (float 0.0-1.0 where 1.0 = very positive), "
            "'summary' (1-2 sentence HR-friendly summary).\n\n"
            f"Exit response:\n{combined_text}"
        )

        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-4",
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                    },
                )
                data = resp.json()
                content = json.loads(data["choices"][0]["message"]["content"])
                interview.sentiment_label = content.get("sentiment")
                interview.sentiment_score = float(content.get("score", 0))
                interview.ai_summary = content.get("summary")
                await db.commit()
        except Exception:
            pass  # Gracefully degrade; raw responses are still saved

    @staticmethod
    async def get_exit_interview(
        db: AsyncSession,
        employee_id: int,
    ) -> Optional[ExitInterview]:
        result = await db.execute(
            select(ExitInterview)
            .where(ExitInterview.employee_id == employee_id)
            .order_by(ExitInterview.submitted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Full & Final Settlement ───────────────────────────────────────────────

    @staticmethod
    async def calculate_settlement(
        db: AsyncSession,
        employee_id: int,
        payload: FnFCalculateRequest,
        hr_user_id: int,
    ) -> FnFSettlement:
        gross = (
            payload.basic_salary
            + payload.hra
            + payload.other_allowances
            + payload.leave_encashment
            + payload.gratuity
            + payload.bonus_payout
            + payload.notice_period_payment
        )
        deductions = (
            payload.notice_period_recovery
            + payload.loan_recovery
            + payload.advance_recovery
            + payload.tax_deduction
            + payload.other_deductions
        )
        net = gross - deductions

        settlement = FnFSettlement(
            employee_id=employee_id,
            resignation_id=payload.resignation_id,
            basic_salary=payload.basic_salary,
            hra=payload.hra,
            other_allowances=payload.other_allowances,
            leave_encashment=payload.leave_encashment,
            gratuity=payload.gratuity,
            bonus_payout=payload.bonus_payout,
            notice_period_payment=payload.notice_period_payment,
            notice_period_recovery=payload.notice_period_recovery,
            loan_recovery=payload.loan_recovery,
            advance_recovery=payload.advance_recovery,
            tax_deduction=payload.tax_deduction,
            other_deductions=payload.other_deductions,
            gross_earnings=round(gross, 2),
            total_deductions=round(deductions, 2),
            net_payable=round(net, 2),
            status=SettlementStatus.CALCULATED,
            calculated_by=hr_user_id,
            calculated_at=datetime.utcnow(),
            remarks=payload.remarks,
        )
        db.add(settlement)
        await db.commit()
        await db.refresh(settlement)
        return settlement

    @staticmethod
    async def get_settlement(db: AsyncSession, employee_id: int) -> Optional[FnFSettlement]:
        result = await db.execute(
            select(FnFSettlement)
            .where(FnFSettlement.employee_id == employee_id)
            .order_by(FnFSettlement.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def approve_settlement(
        db: AsyncSession, settlement_id: int, hr_user_id: int
    ) -> FnFSettlement:
        from fastapi import HTTPException
        s = await db.get(FnFSettlement, settlement_id)
        if not s:
            raise HTTPException(status_code=404, detail="Settlement not found")
        s.status = SettlementStatus.APPROVED
        s.approved_by = hr_user_id
        s.approved_at = datetime.utcnow()
        s.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(s)
        return s

    @staticmethod
    async def mark_settlement_paid(
        db: AsyncSession, settlement_id: int, hr_user_id: int
    ) -> FnFSettlement:
        from fastapi import HTTPException
        s = await db.get(FnFSettlement, settlement_id)
        if not s:
            raise HTTPException(status_code=404, detail="Settlement not found")
        if s.status != SettlementStatus.APPROVED:
            raise HTTPException(
                status_code=400, detail="Settlement must be approved before marking paid."
            )
        s.status = SettlementStatus.PAID
        s.paid_at = datetime.utcnow()
        s.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(s)
        return s

    @staticmethod
    async def generate_settlement_pdf(db: AsyncSession, settlement_id: int):
        """Background task: render settlement breakdown as PDF via WeasyPrint."""
        try:
            from weasyprint import HTML
        except ImportError:
            return
        s = await db.get(FnFSettlement, settlement_id)
        if not s:
            return
        output_dir = os.path.join("uploads", "settlements")
        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, f"fnf_{settlement_id}.pdf")

        html = f"""
        <html><body style="font-family:Arial;font-size:12pt;margin:60px 72px">
        <h2>Full & Final Settlement</h2>
        <table width="100%" cellspacing="4">
          <tr><td><b>Employee ID</b></td><td>{s.employee_id}</td></tr>
          <tr><td colspan="2"><hr/></td></tr>
          <tr><td>Basic Salary</td><td>₹{s.basic_salary:,.2f}</td></tr>
          <tr><td>HRA</td><td>₹{s.hra:,.2f}</td></tr>
          <tr><td>Other Allowances</td><td>₹{s.other_allowances:,.2f}</td></tr>
          <tr><td>Leave Encashment</td><td>₹{s.leave_encashment:,.2f}</td></tr>
          <tr><td>Gratuity</td><td>₹{s.gratuity:,.2f}</td></tr>
          <tr><td>Bonus Payout</td><td>₹{s.bonus_payout:,.2f}</td></tr>
          <tr><td>Notice Period Payment</td><td>₹{s.notice_period_payment:,.2f}</td></tr>
          <tr><td><b>Gross Earnings</b></td><td><b>₹{s.gross_earnings:,.2f}</b></td></tr>
          <tr><td colspan="2"><hr/></td></tr>
          <tr><td>Notice Period Recovery</td><td>₹{s.notice_period_recovery:,.2f}</td></tr>
          <tr><td>Loan Recovery</td><td>₹{s.loan_recovery:,.2f}</td></tr>
          <tr><td>Advance Recovery</td><td>₹{s.advance_recovery:,.2f}</td></tr>
          <tr><td>Tax Deduction (TDS)</td><td>₹{s.tax_deduction:,.2f}</td></tr>
          <tr><td>Other Deductions</td><td>₹{s.other_deductions:,.2f}</td></tr>
          <tr><td><b>Total Deductions</b></td><td><b>₹{s.total_deductions:,.2f}</b></td></tr>
          <tr><td colspan="2"><hr/></td></tr>
          <tr><td><b>Net Payable</b></td><td><b>₹{s.net_payable:,.2f}</b></td></tr>
        </table>
        </body></html>
        """
        HTML(string=html).write_pdf(pdf_path)
        s.pdf_path = pdf_path
        s.updated_at = datetime.utcnow()
        await db.commit()

    # ── Separation Letters ────────────────────────────────────────────────────

    @staticmethod
    async def generate_separation_letters(
        db: AsyncSession,
        employee_id: int,
        letter_types: List[str],
        hr_user_id: int,
    ) -> List[int]:
        """
        Delegates to HRLetterService.issue_letter for each requested type.
        Returns list of created letter IDs.
        """
        from fastapi import HTTPException
        from services.letters_service import HRLetterService
        from schema.HR_Operations.letter_generation import HRLetterIssueRequest

        # Verify pre-conditions
        resignation = await ExitService.get_resignation(db, employee_id)
        if not resignation or resignation.status != ResignationStatus.ACCEPTED:
            raise HTTPException(
                status_code=400,
                detail="Resignation must be ACCEPTED before generating separation letters.",
            )

        LETTER_SUBJECTS = {
            "experience": "Experience Letter",
            "relieving": "Relieving Letter",
        }
        letter_ids = []
        for lt in letter_types:
            req = HRLetterIssueRequest(
                employee_id=employee_id,
                letter_type=LetterType(lt),
                subject=LETTER_SUBJECTS.get(lt, lt.title() + " Letter"),
                body_html=f"<p>This is to certify that Employee ID {employee_id} "
                          f"has been employed with us until "
                          f"{resignation.last_working_day}.</p>",
                issued_on=date.today(),
            )
            letter = await HRLetterService.issue_letter(db, req, hr_user_id)
            await HRLetterService.generate_pdf(db, letter.id)
            letter_ids.append(letter.id)
        return letter_ids

    @staticmethod
    async def send_separation_email(
        db: AsyncSession,
        employee_id: int,
        letter_ids: List[int],
    ):
        """Background: email separation letters to the employee."""
        # Fetch employee email, attach PDFs, send.
        pass

    # ── Analytics ────────────────────────────────────────────────────────────

    @staticmethod
    async def get_exit_analytics(
        db: AsyncSession,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> ExitAnalyticsResponse:
        """
        Aggregated exit analytics.  Uses raw SQLAlchemy aggregates.
        Department filtering requires joining to an Employee/User table
        (left as TODO since schema is platform-specific).
        """
        base_q = select(Resignation).where(Resignation.is_deleted == False)
        if from_date:
            base_q = base_q.where(Resignation.resignation_date >= from_date)
        if to_date:
            base_q = base_q.where(Resignation.resignation_date <= to_date)

        result = await db.execute(base_q)
        resignations = result.scalars().all()

        total = len(resignations)
        accepted = sum(1 for r in resignations if r.status == ResignationStatus.ACCEPTED)
        revoked  = sum(1 for r in resignations if r.status == ResignationStatus.REVOKED)
        pending  = sum(1 for r in resignations if r.status == ResignationStatus.PENDING)

        notice_days = [r.notice_period_days for r in resignations if r.notice_period_days]
        avg_notice = round(sum(notice_days) / len(notice_days), 1) if notice_days else 0

        # Exit reasons frequency
        reason_counts: dict = {}
        for r in resignations:
            key = (r.reason or "Not specified")[:60]
            reason_counts[key] = reason_counts.get(key, 0) + 1
        top_exit_reasons = sorted(
            [{"reason": k, "count": v} for k, v in reason_counts.items()],
            key=lambda x: -x["count"],
        )[:10]

        # Monthly attrition
        monthly: dict = {}
        for r in resignations:
            month = r.resignation_date.strftime("%Y-%m")
            monthly[month] = monthly.get(month, 0) + 1
        monthly_attrition = [{"month": k, "count": v} for k, v in sorted(monthly.items())]

        # Exit interview sentiment
        ei_result = await db.execute(select(ExitInterview))
        interviews = ei_result.scalars().all()
        sentiment_breakdown = {"positive": 0, "neutral": 0, "negative": 0}
        scores: dict = {
            "job_satisfaction": [], "management": [],
            "work_environment": [], "growth_opportunity": [],
        }
        for ei in interviews:
            label = ei.sentiment_label or "neutral"
            if label in sentiment_breakdown:
                sentiment_breakdown[label] += 1
            for dim, key in [
                ("job_satisfaction_score", "job_satisfaction"),
                ("management_score", "management"),
                ("work_environment_score", "work_environment"),
                ("growth_opportunity_score", "growth_opportunity"),
            ]:
                val = getattr(ei, dim)
                if val is not None:
                    scores[key].append(val)

        avg_scores = {
            k: round(sum(v) / len(v), 2) if v else None
            for k, v in scores.items()
        }

        return ExitAnalyticsResponse(
            total_resignations=total,
            accepted=accepted,
            revoked=revoked,
            pending=pending,
            avg_notice_period_days=avg_notice,
            top_exit_reasons=top_exit_reasons,
            monthly_attrition=monthly_attrition,
            sentiment_breakdown=sentiment_breakdown,
            avg_scores=avg_scores,
            department_attrition=[],  # extend with dept join when Employee model available
        )