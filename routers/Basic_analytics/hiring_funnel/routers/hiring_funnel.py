from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse
import csv
from datetime import datetime
from dateutil import parser
from sqlalchemy.orm import Session
from core.database import SessionLocal, Base, engine
from model.models import Candidate

router = APIRouter()

# Create tables automatically (can also move to startup in main.py)
@router.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ Hiring funnel tables created successfully!")
    except Exception as e:
        print(f"⚠ Warning: Could not create hiring funnel tables: {e}")
        print("  Database may not be available. The application will continue.")
        print("  Please ensure PostgreSQL is running and DATABASE_URL is correct.")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper to convert Yes/No/True/False to float
def yes_no_to_float(value):
    if not value:
        return 0.0
    value = str(value).strip().lower()
    if value in ["yes", "1", "true"]:
        return 1.0
    return 0.0

# CSV upload endpoint
@router.post("/upload-file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    decoded = content.decode("utf-8").splitlines()
    reader = csv.DictReader(decoded)

    added_candidates = []
    failed_rows = []

    for i, row in enumerate(reader, start=2):
        try:
            # Parse date
            applied_date_str = row.get("Applied_Date", "")
            try:
                applied_date = datetime.strptime(applied_date_str, "%Y-%m-%d")
            except ValueError:
                try:
                    applied_date = datetime.strptime(applied_date_str, "%d-%m-%Y")
                except ValueError:
                    applied_date = parser.parse(applied_date_str)

            candidate = Candidate(
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
