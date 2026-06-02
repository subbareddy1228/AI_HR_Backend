from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from model.onboarding.documents import OnboardingDocuments
from utils.file_upload import save_file

router = APIRouter(prefix="/api/documents", tags=["Documents"])


def get_or_create(db: Session) -> OnboardingDocuments:
    doc = db.query(OnboardingDocuments).first()
    if not doc:
        doc = OnboardingDocuments(
            pan_card="",
            aadhaar_card="",
            highest_education_proof=""
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    return doc


@router.post("/upload")
def upload_documents(
    pan_card: UploadFile = File(None, description="PAN Card *"),
    aadhaar_card: UploadFile = File(None, description="Aadhaar Card *"),
    highest_education_proof: UploadFile = File(None, description="Highest Education Proof *"),

    esi_card: UploadFile = File(None, description="ESI Card"),
    driving_license: UploadFile = File(None, description="Driving License"),
    passport: UploadFile = File(None, description="Passport"),
    last_relieving_letter: UploadFile = File(None, description="Last Relieving Letter"),
    last_salary_slip: UploadFile = File(None, description="Last Salary Slip"),
    latest_bank_statement: UploadFile = File(None, description="Latest Bank Statement"),

    db: Session = Depends(get_db),
):
    doc = get_or_create(db)

    if pan_card:
        doc.pan_card = save_file(pan_card, "pan_card")

    if aadhaar_card:
        doc.aadhaar_card = save_file(aadhaar_card, "aadhaar_card")

    if highest_education_proof:
        doc.highest_education_proof = save_file(
            highest_education_proof, "highest_education_proof"
        )

    if esi_card:
        doc.esi_card = save_file(esi_card, "esi_card")

    if driving_license:
        doc.driving_license = save_file(driving_license, "driving_license")

    if passport:
        doc.passport = save_file(passport, "passport")

    if last_relieving_letter:
        doc.last_relieving_letter = save_file(
            last_relieving_letter, "last_relieving_letter"
        )

    if last_salary_slip:
        doc.last_salary_slip = save_file(
            last_salary_slip, "last_salary_slip"
        )

    if latest_bank_statement:
        doc.latest_bank_statement = save_file(
            latest_bank_statement, "latest_bank_statement"
        )

    db.commit()

    return {"message": "Documents uploaded successfully"}
