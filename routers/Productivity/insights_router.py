from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_user
from model.Productivity.ProductivityActivity import ProductivityActivity
from services.Productivity.ai_service import identify_productivity_bottlenecks, workload_distribution

router = APIRouter(prefix="/insights", tags=["insights"])

@router.get("/employee/{employee_id}")
def employee_insights(employee_id: int, db: Session = Depends(get_db)):
    activities = db.query(ProductivityActivity).filter(ProductivityActivity.employee_id == employee_id).all()
    data = [{"app_name": a.app_name, "website_url": a.website_url, "productive": a.productive} for a in activities]
    return {
        "bottlenecks": identify_productivity_bottlenecks(data),
        "workload_distribution": workload_distribution(data)
    }
