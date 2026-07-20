from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse
import csv
from datetime import datetime
from dateutil import parser
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, DateTime
from core.database import SessionLocal, Base, engine

router = APIRouter()


class HiringFunnelCandidate(Base):
    __tablename__ = "hiring_funnel_candidates"

    id = Column(Integer, primary_key=True, index=True)
    candidate_name = Column(String, nullable=True)
    source = Column(String, nullable=True)
    applied_date = Column(DateTime, nullable=True)
    role = Column(String, nullable=True)
    location = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    call_screening = Column(Float, nullable=True)
    ai_interview = Column(Float, nullable=True)
    assessment = Column(Float, nullable=True)
    assessment_result = Column(String, nullable=True)
    hired = Column(String, nullable=True)


@router.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Hiring funnel tables created successfully!")
    except Exception as e:
        print(f"⚠ Warning: Could not create hiring funnel tables: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def yes_no_to_float(value):
    if not value:
        return 0.0
    value = str(value).strip().lower()
    if value in ["yes", "1", "true"]:
        return 1.0
    return 0.0


@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    decoded = content.decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)

    added_candidates = []
    failed_rows = []

    for i, row in enumerate(reader, start=2):
        try:
            applied_date_str = row.get("Applied_Date", "")
            try:
                applied_date = datetime.strptime(applied_date_str, "%Y-%m-%d")
            except ValueError:
                try:
                    applied_date = datetime.strptime(applied_date_str, "%d-%m-%Y")
                except ValueError:
                    applied_date = parser.parse(applied_date_str)

            candidate = HiringFunnelCandidate(
                candidate_name=row.get("CandidateName", ""),
                source=row.get("Source", ""),
                applied_date=applied_date,
                role=row.get("Role", ""),
                location=row.get("Location", ""),
                experience_level=row.get("Experience_Level", ""),
                call_screening=yes_no_to_float(row.get("Call_Screening")),
                ai_interview=yes_no_to_float(row.get("AI_Interview")),
                assessment=yes_no_to_float(row.get("Assessment")),
                assessment_result=row.get("Assessment_Result", ""),
                hired=row.get("Hired", ""),
            )

            db.add(candidate)
            added_candidates.append(row.get("CandidateName", ""))

        except Exception as e:
            failed_rows.append({"row": i, "error": str(e), "data": row})

    db.commit()

    return JSONResponse({
        "message": "Upload complete",
        "added_candidates": added_candidates,
        "failed_rows": failed_rows
    })


@router.get("/")
def get_hiring_funnel(db: Session = Depends(get_db)):
    candidates = db.query(HiringFunnelCandidate).all()

    total = len(candidates)
    call_screened = sum(1 for c in candidates if c.call_screening and c.call_screening > 0)
    ai_interviewed = sum(1 for c in candidates if c.ai_interview and c.ai_interview > 0)
    assessed = sum(1 for c in candidates if c.assessment and c.assessment > 0)
    hired = sum(1 for c in candidates if c.hired and str(c.hired).lower() in ["yes", "1", "true"])

    return {
        "total_applicants": total,
        "call_screening": call_screened,
        "ai_interview": ai_interviewed,
        "assessment": assessed,
        "hired": hired,
        "funnel": [
            {"stage": "Applied", "count": total},
            {"stage": "Call Screening", "count": call_screened},
            {"stage": "AI Interview", "count": ai_interviewed},
            {"stage": "Assessment", "count": assessed},
            {"stage": "Hired", "count": hired},
        ]
    }


@router.get("/time-to-hire")
def get_time_to_hire(db: Session = Depends(get_db)):
    candidates = db.query(HiringFunnelCandidate).all()

    if not candidates:
        return {"average_days": 0, "total_hired": 0, "data": []}

    hired_candidates = [
        c for c in candidates
        if c.hired and str(c.hired).lower() in ["yes", "1", "true"] and c.applied_date
    ]

    if not hired_candidates:
        return {"average_days": 0, "total_hired": 0, "data": []}

    today = datetime.utcnow()
    days_list = []
    for c in hired_candidates:
        applied = c.applied_date if isinstance(c.applied_date, datetime) else datetime.combine(c.applied_date, datetime.min.time())
        delta = (today - applied).days
        days_list.append({"name": c.candidate_name, "days": delta, "role": c.role})

    avg_days = sum(d["days"] for d in days_list) / len(days_list) if days_list else 0

    return {
        "average_days": round(avg_days, 1),
        "total_hired": len(hired_candidates),
        "data": days_list
    }