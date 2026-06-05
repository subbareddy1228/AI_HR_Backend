from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from services.Productivity.dashboard_services import get_dashboard_data
from core.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
def dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return get_dashboard_data(db)
