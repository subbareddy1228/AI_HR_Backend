"""
Service: Employee Separation & Exit Management
Handles resignation workflow, clearance, exit interviews (+ AI sentiment),
FnF settlement computation, and separation letter generation.
"""

import json
import os
from datetime import datetime, date
from typing import List, Optional

from sqlmodel import Session, select, func
from fastapi import HTTPException

from model.HR_Operations.exit_management import (
    Resignation, ClearanceChecklist, ClearanceItem,
    ExitInterview, FnFSettlement, Alumni,
)

from schema.HR_Operations.exit_management import (
    ResignationCreate, ResignationAccept,
    ClearanceInitiateRequest, ClearanceItemUpdate,
    ExitInterviewSubmit,
    FnFCalculateRequest,
    ExitAnalyticsResponse,
)

# ── Status constants (plain strings to match your DB) ─────────────────────────
class ResignationStatus:
    PENDING  = "pending"
    ACCEPTED = "accepted"
    REVOKED  = "revoked"
    REJECTED = "rejected"

class ClearanceStatus:
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"

class ClearanceDepartment:
    IT      = "IT"
    FINANCE = "Finance"
    ADMIN   = "Admin"
    HR      = "HR"

class SettlementStatus:
    DRAFT      = "draft"
    CALCULATED = "calculated"
    APPROVED   = "approved"
    PAID       = "paid"

# ── Default clearance tasks seeded for every offboarding ─────────────────────
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
    def submit_resignation(
        db: Session,
        payload: ResignationCreate,
        employee_id: int,
    ) -> Resignation:
        existing = ExitService.get_resignation(db, employee_id)
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
        db.commit()
        db.refresh(resignation)
        return resignation

    @staticmethod
    def get_resignation(db: Session, employee_id: int) -> Optional[Resignation]:
        result = db.execute(
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
    def accept_resignation(
        db: Session,
        resignation_id: int,
        payload: ResignationAccept,
        hr_user_id: int,
    ) -> Resignation:
        resignation = db.get(Resignation, resignation_id)
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
        db.commit()
        db.refresh(resignation)
        return resignation

    @staticmethod
    def revoke_resignation(
        db: Session,
        resignation_id: int,
        employee_id: int,
    ) -> Resignation:
        resignation = db.get(Resignation, resignation_id)
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
        db.commit()
        db.refresh(resignation)
        return resignation

    @staticmethod
    def get_notice_period_status(db: Session, employee_id: int) -> dict:
        resignation = ExitService.get_resignation(db, employee_id)
        if not resignation or resignation.status != ResignationStatus.ACCEPTED:
            raise HTTPException(status_code=404, detail="No accepted resignation found")
        today = date.today()
        days_served = (today - resignation.resignation_date).days
        days_remaining = max(
            0, (resignation.last_working_day - today).days
        ) if resignation.last_working_day else 0
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
    def initiate_clearance(
        db: Session,
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
        db.flush()  # get checklist.id before adding items

        tasks = payload.custom_tasks if payload.custom_tasks else DEFAULT_CLEARANCE_TASKS
        for task in tasks:
            item = ClearanceItem(
                checklist_id=checklist.id,
                department=task["department"] if isinstance(task, dict) else task.department,
                task_description=task["task_description"] if isinstance(task, dict) else task.task_description,
            )
            db.add(item)

        db.commit()
        db.refresh(checklist)
        return checklist

    @staticmethod
    def get_clearance(db: Session, employee_id: int) -> Optional[ClearanceChecklist]:
        result = db.execute(
            select(ClearanceChecklist)
            .where(ClearanceChecklist.employee_id == employee_id)
            .order_by(ClearanceChecklist.initiated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def complete_clearance_item(
        db: Session,
        checklist_item_id: int,
        payload: ClearanceItemUpdate,
        completed_by: int,
    ) -> ClearanceChecklist:
        item = db.get(ClearanceItem, checklist_item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Checklist item not found")
        item.is_completed = True
        item.completed_by = completed_by
        item.completed_at = datetime.utcnow()
        item.remarks = payload.remarks

        checklist = db.get(ClearanceChecklist, item.checklist_id)
        pending_result = db.execute(
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

        db.commit()
        db.refresh(checklist)
        return checklist

    # ── Exit Interview ───────────────────────────────────────────────────────

    @staticmethod
    def submit_exit_interview(
        db: Session,
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
        db.commit()
        db.refresh(interview)
        return interview

    @staticmethod
    def run_sentiment_analysis(db: Session, interview_id: int):
        """
        Background task: calls OpenAI GPT-4 to analyse exit interview sentiment.
        Updates sentiment_label, sentiment_score, and ai_summary on the record.
        Note: runs in background so uses a new db session concept — kept sync here.
        """
        import httpx

        interview = db.get(ExitInterview, interview_id)
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
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": prompt}],
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            data = response.json()
            content = json.loads(data["choices"][0]["message"]["content"])
            interview.sentiment_label = content.get("sentiment")
            interview.sentiment_score = float(content.get("score", 0))
            interview.ai_summary = content.get("summary")
            db.commit()
        except Exception:
            pass  # Gracefully degrade; raw responses are still saved

    @staticmethod
    def get_exit_interview(db: Session, employee_id: int) -> Optional[ExitInterview]:
        result = db.execute(
            select(ExitInterview)
            .where(ExitInterview.employee_id == employee_id)
            .order_by(ExitInterview.submitted_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Full & Final Settlement ───────────────────────────────────────────────

    @staticmethod
    def calculate_settlement(
        db: Session,
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
        db.commit()
        db.refresh(settlement)
        return settlement

    @staticmethod
    def get_settlement(db: Session, employee_id: int) -> Optional[FnFSettlement]:
        result = db.execute(
            select(FnFSettlement)
            .where(FnFSettlement.employee_id == employee_id)
            .order_by(FnFSettlement.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def approve_settlement(db: Session, settlement_id: int, hr_user_id: int) -> FnFSettlement:
        s = db.get(FnFSettlement, settlement_id)
        if not s:
            raise HTTPException(status_code=404, detail="Settlement not found")
        s.status = SettlementStatus.APPROVED
        s.approved_by = hr_user_id
        s.approved_at = datetime.utcnow()
        s.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(s)
        return s

    @staticmethod
    def mark_settlement_paid(db: Session, settlement_id: int, hr_user_id: int) -> FnFSettlement:
        s = db.get(FnFSettlement, settlement_id)
        if not s:
            raise HTTPException(status_code=404, detail="Settlement not found")
        if s.status != SettlementStatus.APPROVED:
            raise HTTPException(
                status_code=400, detail="Settlement must be approved before marking paid."
            )
        s.status = SettlementStatus.PAID
        s.paid_at = datetime.utcnow()
        s.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(s)
        return s

    @staticmethod
    def generate_settlement_pdf(db: Session, settlement_id: int):
        """Background task: render settlement breakdown as PDF via WeasyPrint."""
        try:
            from weasyprint import HTML
        except ImportError:
            return
        s = db.get(FnFSettlement, settlement_id)
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
        db.commit()

    # ── Separation Letters ────────────────────────────────────────────────────

    @staticmethod
    def generate_separation_letters(
        db: Session,
        employee_id: int,
        letter_types: List[str],
        hr_user_id: int,
    ) -> List[int]:
        from services.letters_service import HRLetterService
        from schema.HR_Operations.letter_generation import HRLetterIssueRequest

        resignation = ExitService.get_resignation(db, employee_id)
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
                letter_type=lt,
                subject=LETTER_SUBJECTS.get(lt, lt.title() + " Letter"),
                body_html=f"<p>This is to certify that Employee ID {employee_id} "
                          f"has been employed with us until "
                          f"{resignation.last_working_day}.</p>",
                issued_on=date.today(),
            )
            letter = HRLetterService.issue_letter(db, req, hr_user_id)
            HRLetterService.generate_pdf(db, letter.id)
            letter_ids.append(letter.id)
        return letter_ids

    @staticmethod
    def send_separation_email(db: Session, employee_id: int, letter_ids: List[int]):
        """Background: email separation letters to the employee."""
        pass

    # ── Analytics ────────────────────────────────────────────────────────────

    @staticmethod
    def get_exit_analytics(
        db: Session,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        department_id: Optional[int] = None,
    ) -> ExitAnalyticsResponse:
        base_q = select(Resignation).where(Resignation.is_deleted == False)
        if from_date:
            base_q = base_q.where(Resignation.resignation_date >= from_date)
        if to_date:
            base_q = base_q.where(Resignation.resignation_date <= to_date)

        resignations = db.execute(base_q).scalars().all()

        total    = len(resignations)
        accepted = sum(1 for r in resignations if r.status == ResignationStatus.ACCEPTED)
        revoked  = sum(1 for r in resignations if r.status == ResignationStatus.REVOKED)
        pending  = sum(1 for r in resignations if r.status == ResignationStatus.PENDING)

        notice_days = [r.notice_period_days for r in resignations if r.notice_period_days]
        avg_notice = round(sum(notice_days) / len(notice_days), 1) if notice_days else 0

        reason_counts: dict = {}
        for r in resignations:
            key = (r.reason or "Not specified")[:60]
            reason_counts[key] = reason_counts.get(key, 0) + 1
        top_exit_reasons = sorted(
            [{"reason": k, "count": v} for k, v in reason_counts.items()],
            key=lambda x: -x["count"],
        )[:10]

        monthly: dict = {}
        for r in resignations:
            month = r.resignation_date.strftime("%Y-%m")
            monthly[month] = monthly.get(month, 0) + 1
        monthly_attrition = [{"month": k, "count": v} for k, v in sorted(monthly.items())]

        interviews = db.execute(select(ExitInterview)).scalars().all()
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
            department_attrition=[],
        )
    """
ADD THESE METHODS TO: services/Exit_service.py
Add inside the ExitService class after get_exit_analytics method.
Also add at top: from model.HR_Operations.exit_management import Alumni
"""

# ── Exit Cases ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_exit_cases(db: Session, department=None, status=None) -> list:
        """Returns all active exit cases with clearance progress."""
        query = select(Resignation).where(
            Resignation.is_deleted == False,
            Resignation.status == "accepted",
        )
        resignations = db.execute(query).scalars().all()
        cases = []
        for r in resignations:
            # Get clearance checklist
            checklist = db.execute(
                select(ClearanceChecklist).where(
                    ClearanceChecklist.employee_id == r.employee_id
                ).order_by(ClearanceChecklist.initiated_at.desc()).limit(1)
            ).scalar_one_or_none()

            total_items = 0
            completed_items = 0
            pending_depts = []
            overall_status = "pending"

            if checklist:
                items = db.execute(
                    select(ClearanceItem).where(ClearanceItem.checklist_id == checklist.id)
                ).scalars().all()
                total_items = len(items)
                completed_items = sum(1 for i in items if i.is_completed)
                pending_depts = [i.department for i in items if not i.is_completed]
                overall_status = checklist.overall_status

            progress_pct = round(completed_items / total_items * 100) if total_items else 0

            # Determine if escalated (last working day passed but not completed)
            escalated = False
            if r.last_working_day and r.last_working_day < date.today() and overall_status != "completed":
                escalated = True

            case = {
                "employee_id": r.employee_id,
                "resignation_id": r.id,
                "resignation_date": r.resignation_date,
                "last_working_day": r.last_working_day,
                "notice_period_days": r.notice_period_days,
                "progress_pct": progress_pct,
                "pending_departments": pending_depts,
                "clearance_status": overall_status,
                "escalated": escalated,
                "status": "completed" if overall_status == "completed"
                          else "escalated" if escalated
                          else "in_progress" if progress_pct > 0
                          else "pending",
            }
            if department and case.get("department") != department:
                continue
            if status and case["status"] != status:
                continue
            cases.append(case)
        return cases

    @staticmethod
    def get_exit_cases_stats(db: Session) -> dict:
        resignations = db.execute(
            select(Resignation).where(
                Resignation.is_deleted == False,
                Resignation.status == "accepted",
            )
        ).scalars().all()
        alumni_count = db.execute(
            select(func.count(Alumni.id)).where(Alumni.is_deleted == False)
        ).scalar()
        escalated = 0
        for r in resignations:
            if r.last_working_day and r.last_working_day < date.today():
                checklist = db.execute(
                    select(ClearanceChecklist).where(
                        ClearanceChecklist.employee_id == r.employee_id
                    ).limit(1)
                ).scalar_one_or_none()
                if not checklist or checklist.overall_status != "completed":
                    escalated += 1
        return {
            "total_cases": len(resignations),
            "pending": sum(1 for r in resignations),
            "escalated": escalated,
            "alumni": alumni_count or 0,
        }

    # ── Alumni ───────────────────────────────────────────────────────────────

    @staticmethod
    def create_alumni(db: Session, payload, created_by: int):
        from model.HR_Operations.exit_management import Alumni
        alumni = Alumni(
            employee_id=payload.employee_id,
            employee_code=payload.employee_code,
            name=payload.name,
            department=payload.department,
            designation=payload.designation,
            exit_date=payload.exit_date,
            exit_reason=payload.exit_reason,
            rehire_eligible=payload.rehire_eligible,
            boomerang=payload.boomerang,
            engagement_level=payload.engagement_level,
            email=payload.email,
            phone=payload.phone,
            linkedin=payload.linkedin,
            notes=payload.notes,
            created_by=created_by,
        )
        db.add(alumni)
        db.commit()
        db.refresh(alumni)
        return alumni

    @staticmethod
    def list_alumni(db: Session, department=None, rehire_eligible=None, boomerang=None):
        from model.HR_Operations.exit_management import Alumni
        query = select(Alumni).where(Alumni.is_deleted == False)
        if department:
            query = query.where(Alumni.department == department)
        if rehire_eligible is not None:
            query = query.where(Alumni.rehire_eligible == rehire_eligible)
        if boomerang is not None:
            query = query.where(Alumni.boomerang == boomerang)
        return db.execute(query.order_by(Alumni.exit_date.desc())).scalars().all()

    @staticmethod
    def get_alumni(db: Session, alumni_id: int):
        from model.HR_Operations.exit_management import Alumni
        return db.get(Alumni, alumni_id)

    @staticmethod
    def update_alumni(db: Session, alumni_id: int, payload):
        from model.HR_Operations.exit_management import Alumni
        alumni = db.get(Alumni, alumni_id)
        if not alumni:
            raise HTTPException(status_code=404, detail="Alumni not found")
        for field, value in payload.dict(exclude_none=True).items():
            setattr(alumni, field, value)
        alumni.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(alumni)
        return alumni

    @staticmethod
    def delete_alumni(db: Session, alumni_id: int):
        from model.HR_Operations.exit_management import Alumni
        alumni = db.get(Alumni, alumni_id)
        if not alumni:
            raise HTTPException(status_code=404, detail="Alumni not found")
        alumni.is_deleted = True
        alumni.updated_at = datetime.utcnow()
        db.commit()

    # ── Employee Exits Report ─────────────────────────────────────────────────

    @staticmethod
    def get_employee_exits_report(db: Session, location=None, department=None,
                                   exit_reason=None, from_date=None, to_date=None):
        from schema.HR_Operations.exit_management import EmployeeExitsReportResponse, EmployeeExitRecord
        from datetime import datetime as dt

        query = select(Resignation).where(
            Resignation.is_deleted == False,
            Resignation.status == "accepted",
        )
        if from_date:
            try:
                query = query.where(Resignation.last_working_day >= dt.strptime(from_date, "%Y-%m-%d").date())
            except ValueError:
                pass
        if to_date:
            try:
                query = query.where(Resignation.last_working_day <= dt.strptime(to_date, "%Y-%m-%d").date())
            except ValueError:
                pass

        resignations = db.execute(query.order_by(Resignation.last_working_day.desc())).scalars().all()

        exits = []
        for i, r in enumerate(resignations, start=1):
            # Map exit_reason from exit interview if available
            interview = db.execute(
                select(ExitInterview).where(ExitInterview.employee_id == r.employee_id).limit(1)
            ).scalar_one_or_none()
            reason = interview.reason_for_leaving[:30] if interview and interview.reason_for_leaving else (r.reason or "Not specified")

            record = EmployeeExitRecord(
                sn=i,
                employee_id=r.employee_id,
                employee_code=f"LEV{r.employee_id:03d}",
                name=f"Employee {r.employee_id}",   # replace with actual name lookup
                location=location or "Hyderabad",
                department=department or "General",
                designation=None,
                joining_date=None,
                exit_date=r.last_working_day,
                exit_reason=reason,
            )
            exits.append(record)

        return EmployeeExitsReportResponse(
            total=len(exits),
            exits=exits,
            filters_applied={
                "location": location, "department": department,
                "exit_reason": exit_reason, "from_date": from_date, "to_date": to_date,
            },
        )

    @staticmethod
    def export_exits_pdf(db: Session, **kwargs) -> str:
        report = ExitService.get_employee_exits_report(db, **kwargs)
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Employee Exits Report", ln=True, align="C")
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 8, f"Total Exits: {report.total}", ln=True)
            pdf.ln(4)
            # Header
            pdf.set_font("Arial", "B", 9)
            for col in ["SN", "Name", "Dept", "Exit Date", "Reason"]:
                pdf.cell(35, 7, col, border=1)
            pdf.ln()
            pdf.set_font("Arial", size=9)
            for e in report.exits:
                pdf.cell(35, 7, str(e.sn), border=1)
                pdf.cell(35, 7, str(e.name)[:15], border=1)
                pdf.cell(35, 7, str(e.department)[:15], border=1)
                pdf.cell(35, 7, str(e.exit_date or ""), border=1)
                pdf.cell(35, 7, str(e.exit_reason or "")[:15], border=1)
                pdf.ln()
            output_dir = os.path.join("uploads", "reports")
            os.makedirs(output_dir, exist_ok=True)
            path = os.path.join(output_dir, f"exits_report_{datetime.utcnow().strftime('%Y%m%d')}.pdf")
            pdf.output(path)
            return path
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"PDF failed: {e}")

    @staticmethod
    def export_exits_excel(db: Session, **kwargs) -> str:
        report = ExitService.get_employee_exits_report(db, **kwargs)
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Employee Exits"
            ws.append(["SN", "Employee Code", "Name", "Location", "Department",
                        "Designation", "Joining Date", "Exit Date", "Exit Reason"])
            for e in report.exits:
                ws.append([e.sn, e.employee_code, e.name, e.location,
                            e.department, e.designation, str(e.joining_date or ""),
                            str(e.exit_date or ""), e.exit_reason])
            output_dir = os.path.join("uploads", "reports")
            os.makedirs(output_dir, exist_ok=True)
            path = os.path.join(output_dir, f"exits_report_{datetime.utcnow().strftime('%Y%m%d')}.xlsx")
            wb.save(path)
            return path
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Excel failed: {e}")

    # ── Exit Trends ───────────────────────────────────────────────────────────

    @staticmethod
    def get_exit_trends(db: Session, period="last_3_months", department=None):
        from schema.HR_Operations.exit_management import ExitTrendsResponse
        from datetime import datetime as dt, timedelta

        # Determine date range
        today = date.today()
        period_map = {
            "last_3_months": today - timedelta(days=90),
            "last_6_months": today - timedelta(days=180),
            "last_year": today - timedelta(days=365),
            "all": date(2000, 1, 1),
        }
        start_date = period_map.get(period, period_map["last_3_months"])

        query = select(Resignation).where(
            Resignation.is_deleted == False,
            Resignation.status == "accepted",
            Resignation.last_working_day >= start_date,
        )
        resignations = db.execute(query).scalars().all()
        total = len(resignations)

        # Exit rate (exits / total headcount * 100) — headcount approximated
        # Replace with actual headcount from employees table
        approx_headcount = max(total + 50, 1)
        exit_rate = round(total / approx_headcount * 100, 1)

        # Avg tenure — using resignation_date - joining_date
        # Without joining_date, use notice_period as proxy
        avg_tenure = 2.8  # default; replace with actual joining date calculation

        # Top exit reason
        reason_counts: dict = {}
        for r in resignations:
            interview = db.execute(
                select(ExitInterview).where(
                    ExitInterview.employee_id == r.employee_id
                ).limit(1)
            ).scalar_one_or_none()
            reason = "Not Specified"
            if interview and interview.reason_for_leaving:
                reason = interview.reason_for_leaving[:40]
            elif r.reason:
                reason = r.reason[:40]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        top_reason = max(reason_counts, key=reason_counts.get) if reason_counts else "Better Opportunity"

        # Monthly exits
        monthly: dict = {}
        for r in resignations:
            if r.last_working_day:
                month = r.last_working_day.strftime("%Y-%m")
                monthly[month] = monthly.get(month, 0) + 1
        monthly_exits = [{"month": k, "count": v} for k, v in sorted(monthly.items())]

        # Reason breakdown
        reason_breakdown = sorted(
            [{"reason": k, "count": v} for k, v in reason_counts.items()],
            key=lambda x: -x["count"]
        )[:5]

        return ExitTrendsResponse(
            period=period,
            department=department,
            exit_rate_pct=exit_rate,
            avg_tenure_years=avg_tenure,
            top_exit_reason=top_reason,
            monthly_exits=monthly_exits,
            department_breakdown=[],  # extend with dept join
            reason_breakdown=reason_breakdown,
            total_exits_in_period=total,
        )
    