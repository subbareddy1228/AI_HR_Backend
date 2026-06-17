
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from core.database import get_db
import services.Payroll.slip_service as svc
from schema.Payroll.salary_slip import (
    SalarySlipCreate, SalarySlipUpdate, SalarySlipResponse,
    GenerateSlipRequest, GenerateAllRequest, GenerateSlipResponse,
    SlipHistoryResponse, ExportRequest, PrintReportRequest,
    DistributeSlipRequest, BulkDistributeRequest,
    DistributionSettingsUpdate, DistributionSettingsResponse,
    SalarySlipDistributionResponse,
    SalarySlipConfigCreate, SalarySlipConfigUpdate, SalarySlipConfigResponse,
    SalarySlipDashboard,
)

router = APIRouter(prefix="/salary-slips", tags=["Payroll - Salary Slips"])


@router.get("/dashboard", response_model=SalarySlipDashboard)
def get_dashboard(db: Session = Depends(get_db)):

    return svc.get_dashboard(db)



@router.post(
    "/generate",
    response_model=SalarySlipResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_slip(payload: GenerateSlipRequest, db: Session = Depends(get_db)):

    return svc.generate_slip(db, payload)


@router.post(
    "/generate/all",
    response_model=GenerateSlipResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_all(payload: GenerateAllRequest, db: Session = Depends(get_db)):

    return svc.generate_all_slips(db, payload)


@router.get("/generate/preview")
def slip_preview(
    employee_id: int = Query(...),
    month:       int = Query(..., ge=1, le=12),
    year:        int = Query(...),
    db: Session = Depends(get_db),
):

    return svc.get_slip_preview(db, employee_id, month, year)



@router.get("/history", response_model=SlipHistoryResponse)
def get_history(
    search:      Optional[str] = Query(None, description="Search by name, ID, month or status"),
    slip_month:  Optional[int] = Query(None, ge=1, le=12),
    slip_year:   Optional[int] = Query(None),
    slip_status: Optional[str] = Query(None),
    employee_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):

    return svc.get_slip_history(
        db,
        search=search,
        slip_month=slip_month,
        slip_year=slip_year,
        slip_status=slip_status,
        employee_id=employee_id,
    )


@router.get("/bulk-download")
def bulk_download(
    slip_ids: Optional[str] = Query(None, description="Comma-separated slip IDs"),
    db: Session = Depends(get_db),
):

    ids = [int(i) for i in slip_ids.split(",")] if slip_ids else None
    slips = svc.bulk_download(db, ids)
    return {
        "total": len(slips),
        "slips": [
            {
                "id": s.id,
                "slip_code": s.slip_code,
                "employee_name": s.employee_name,
                "pay_period": f"{s.slip_month}/{s.slip_year}",
                "pdf_path": s.pdf_path,
            }
            for s in slips
        ],
    }


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
def bulk_delete(slip_ids: List[int], db: Session = Depends(get_db)):

    deleted = svc.delete_slips_bulk(db, slip_ids)
    return {"deleted": deleted}


@router.post("/export")
def export_slips(payload: ExportRequest, db: Session = Depends(get_db)):

    return svc.export_slips(db, payload)


@router.post("/print-reports")
def print_reports(payload: PrintReportRequest, db: Session = Depends(get_db)):
    
    export_req = ExportRequest(
        pay_period_month=payload.pay_period_month,
        pay_period_year=payload.pay_period_year,
        format="pdf",
    )
    return svc.export_slips(db, export_req)


@router.get("/distribution/settings", response_model=DistributionSettingsResponse)
def get_distribution_settings(db: Session = Depends(get_db)):

    return svc.get_distribution_settings(db)


@router.put("/distribution/settings", response_model=DistributionSettingsResponse)
def update_distribution_settings(
    payload: DistributionSettingsUpdate, db: Session = Depends(get_db)
):

    return svc.update_distribution_settings(db, payload)


@router.post("/distribution/settings/reset", response_model=DistributionSettingsResponse)
def reset_distribution_settings(db: Session = Depends(get_db)):

    return svc.reset_distribution_settings(db)


@router.post(
    "/distribution/settings/reset-template",
    response_model=DistributionSettingsResponse,
)
def reset_email_template(db: Session = Depends(get_db)):
   
    return svc.reset_email_template(db)


@router.post(
    "/distribution/{slip_id}/send",
    response_model=SalarySlipDistributionResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_slip(
    slip_id: int,
    payload: DistributeSlipRequest,
    db: Session = Depends(get_db),
):

    payload.slip_id = slip_id
    return svc.distribute_slip(db, payload)


@router.post("/distribution/bulk")
def bulk_distribute(payload: BulkDistributeRequest, db: Session = Depends(get_db)):

    return svc.bulk_distribute(db, payload)


@router.get(
    "/distribution/{slip_id}/records",
    response_model=List[SalarySlipDistributionResponse],
)
def get_distribution_records(slip_id: int, db: Session = Depends(get_db)):

    from sqlalchemy import select
    from model.Payroll.salary_slip import SalarySlipDistribution
    records = db.execute(
        select(SalarySlipDistribution)
        .where(SalarySlipDistribution.slip_id == slip_id)
        .order_by(SalarySlipDistribution.created_at.desc())
    ).scalars().all()
    return records


@router.get("/settings", response_model=SalarySlipConfigResponse)
def get_settings(db: Session = Depends(get_db)):
    
    return svc.get_slip_config(db)


@router.post(
    "/settings",
    response_model=SalarySlipConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_settings(payload: SalarySlipConfigCreate, db: Session = Depends(get_db)):

    return svc.create_slip_config(db, payload)


@router.put("/settings", response_model=SalarySlipConfigResponse)
def update_settings(payload: SalarySlipConfigUpdate, db: Session = Depends(get_db)):

    return svc.update_slip_config(db, payload)


@router.post("/settings/reset", response_model=SalarySlipConfigResponse)
def reset_settings(db: Session = Depends(get_db)):

    return svc.reset_slip_config(db)


@router.put("/settings/advanced", response_model=SalarySlipConfigResponse)
def update_advanced_settings(
    payload: SalarySlipConfigUpdate, db: Session = Depends(get_db)
):

    return svc.update_slip_config(db, payload)


@router.post(
    "/",
    response_model=SalarySlipResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_salary_slip(payload: SalarySlipCreate, db: Session = Depends(get_db)):
    return svc.create_salary_slip(db, payload)


@router.get("/", response_model=List[SalarySlipResponse])
def list_salary_slips(
    employee_id: Optional[int] = Query(None),
    slip_month:  Optional[int] = Query(None),
    slip_year:   Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_salary_slips(db, employee_id, slip_month, slip_year)


@router.get("/employee/{employee_id}", response_model=List[SalarySlipResponse])
def get_slips_by_employee(employee_id: int, db: Session = Depends(get_db)):
    return svc.get_slips_by_employee(db, employee_id)


@router.get("/{slip_id}", response_model=SalarySlipResponse)
def get_salary_slip(slip_id: int, db: Session = Depends(get_db)):
    return svc.get_salary_slip(db, slip_id)


@router.patch("/{slip_id}/publish", response_model=SalarySlipResponse)
def publish_salary_slip(slip_id: int, db: Session = Depends(get_db)):
    return svc.publish_salary_slip(db, slip_id)


@router.put("/{slip_id}", response_model=SalarySlipResponse)
def update_salary_slip(
    slip_id: int, payload: SalarySlipUpdate, db: Session = Depends(get_db)
):
    return svc.update_salary_slip(db, slip_id, payload)


@router.delete("/{slip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salary_slip(slip_id: int, db: Session = Depends(get_db)):
    svc.delete_salary_slip(db, slip_id)