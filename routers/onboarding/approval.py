from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from model.onboarding.onboarding import OnboardingForm
from model.onboarding.employee import Employee
from schema.onboarding.employee import EmployeeCreate

router = APIRouter(prefix="/approval", tags=["Approval"])

@router.post("/{onboarding_id}")
def approve_onboarding(onboarding_id: int, data: EmployeeCreate, db: Session = Depends(get_db)):
    form = db.query(OnboardingForm).filter_by(id=onboarding_id).first()
    if not form:
        raise HTTPException(404, "Onboarding form not found")

    form.status = "APPROVED"
    employee = Employee(onboarding_id=form.id, employee_code=f"EMP{form.id:04d}", **data.dict())
    db.add(employee)
    db.commit()
    return {"message": "Employee created successfully"}
