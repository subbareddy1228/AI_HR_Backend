
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from core.database import get_db
import services.Payroll.statutory_service as svc
from schema.Payroll.statutory_compliance import (

    StatutoryConfigCreate, StatutoryConfigUpdate, StatutoryConfigResponse,
    PFEligibilityRuleCreate, PFEligibilityRuleUpdate, PFEligibilityRuleResponse,
    PFStatementCreate, PFStatementUpdate, PFStatementResponse,
    PFRemittanceSummaryCreate, PFRemittanceSummaryUpdate, PFRemittanceSummaryResponse,
    ECRRecordCreate, ECRRecordUpdate, ECRRecordResponse,
    VPFRecordCreate, VPFRecordUpdate, VPFRecordResponse,
    UANRecordCreate, UANRecordUpdate, UANRecordResponse,
    StatutoryDashboard, StatutoryCompliancePageResponse,
)

router = APIRouter(prefix="/statutory", tags=["Payroll - Statutory Compliance"])

_now = datetime.now()


@router.get("/", response_model=StatutoryCompliancePageResponse)
def get_compliance_page(
    month: int = Query(default=_now.month, ge=1, le=12),
    year:  int = Query(default=_now.year),
    db: Session = Depends(get_db),
):

    return svc.get_compliance_page(db, month, year)


@router.get("/dashboard", response_model=StatutoryDashboard)
def get_dashboard(
    month: int = Query(default=_now.month, ge=1, le=12),
    year:  int = Query(default=_now.year),
    db: Session = Depends(get_db),
):
   
    return svc.get_statutory_dashboard(db, month, year)


@router.get("/config", response_model=StatutoryConfigResponse)
def get_config(db: Session = Depends(get_db)):
    return svc.get_statutory_config(db)


@router.post(
    "/config",
    response_model=StatutoryConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_config(payload: StatutoryConfigCreate, db: Session = Depends(get_db)):
    return svc.create_statutory_config(db, payload)


@router.put("/config/{config_id}", response_model=StatutoryConfigResponse)
def update_config(
    config_id: int, payload: StatutoryConfigUpdate, db: Session = Depends(get_db)
):

    return svc.update_statutory_config(db, config_id, payload)


@router.get("/eligibility", response_model=Optional[PFEligibilityRuleResponse])
def get_eligibility(db: Session = Depends(get_db)):
    config = svc.get_statutory_config(db)
    return svc.get_eligibility_rule(db, config.id)


@router.put("/eligibility", response_model=PFEligibilityRuleResponse)
def upsert_eligibility(
    payload: PFEligibilityRuleCreate, db: Session = Depends(get_db)
):

    return svc.upsert_eligibility_rule(db, payload)


@router.put("/eligibility/{rule_id}", response_model=PFEligibilityRuleResponse)
def update_eligibility(
    rule_id: int, payload: PFEligibilityRuleUpdate, db: Session = Depends(get_db)
):
    return svc.update_eligibility_rule(db, rule_id, payload)

@router.get("/pf-statements", response_model=List[PFStatementResponse])
def list_pf_statements(
    month: int = Query(default=_now.month, ge=1, le=12),
    year:  int = Query(default=_now.year),
    db: Session = Depends(get_db),
):
    return svc.list_pf_statements(db, month, year)


@router.post(
    "/pf-statements",
    response_model=PFStatementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pf_statement(payload: PFStatementCreate, db: Session = Depends(get_db)):
    return svc.create_pf_statement(db, payload)


@router.put("/pf-statements/{statement_id}", response_model=PFStatementResponse)
def update_pf_statement(
    statement_id: int, payload: PFStatementUpdate, db: Session = Depends(get_db)
):
    return svc.update_pf_statement(db, statement_id, payload)


@router.post(
    "/pf-statements/generate",
    response_model=List[PFStatementResponse],
    status_code=status.HTTP_201_CREATED,
)
def generate_pf_statements(
    month: int = Query(ge=1, le=12),
    year:  int = Query(),
    db: Session = Depends(get_db),
):

    return svc.generate_pf_statements_from_payroll(db, month, year)


@router.get("/remittance", response_model=List[PFRemittanceSummaryResponse])
def list_remittance(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_remittance_summary(db, year=year)


@router.post(
    "/remittance",
    response_model=PFRemittanceSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_remittance(
    payload: PFRemittanceSummaryCreate, db: Session = Depends(get_db)
):

    return svc.create_remittance_summary(db, payload)


@router.put("/remittance/{summary_id}", response_model=PFRemittanceSummaryResponse)
def update_remittance(
    summary_id: int, payload: PFRemittanceSummaryUpdate, db: Session = Depends(get_db)
):
    return svc.update_remittance_summary(db, summary_id, payload)


@router.post("/remittance/generate", response_model=PFRemittanceSummaryResponse)
def generate_remittance(
    month: int = Query(ge=1, le=12),
    year:  int = Query(),
    db: Session = Depends(get_db),
):
 
    return svc.generate_remittance_from_statements(db, month, year)


@router.get("/ecr", response_model=List[ECRRecordResponse])
def list_ecr(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return svc.list_ecr_records(db, year=year)


@router.post(
    "/ecr",
    response_model=ECRRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_ecr(payload: ECRRecordCreate, db: Session = Depends(get_db)):
    return svc.create_ecr_record(db, payload)


@router.put("/ecr/{ecr_id}", response_model=ECRRecordResponse)
def update_ecr(
    ecr_id: int, payload: ECRRecordUpdate, db: Session = Depends(get_db)
):
    return svc.update_ecr_record(db, ecr_id, payload)


@router.post("/ecr/generate", response_model=ECRRecordResponse)
def generate_ecr(
    month: int = Query(ge=1, le=12),
    year:  int = Query(),
    db: Session = Depends(get_db),
):

    return svc.generate_ecr_from_statements(db, month, year)


@router.post("/ecr/{ecr_id}/submit", response_model=ECRRecordResponse)
def submit_ecr(
    ecr_id: int,
    ack_number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
   
    return svc.submit_ecr(db, ecr_id, ack_number=ack_number)


@router.get("/vpf", response_model=List[VPFRecordResponse])
def list_vpf(
    month: int = Query(default=_now.month, ge=1, le=12),
    year:  int = Query(default=_now.year),
    db: Session = Depends(get_db),
):
    return svc.list_vpf_records(db, month, year)


@router.post(
    "/vpf",
    response_model=VPFRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vpf(payload: VPFRecordCreate, db: Session = Depends(get_db)):

    return svc.create_vpf_record(db, payload)


@router.put("/vpf/{vpf_id}", response_model=VPFRecordResponse)
def update_vpf(
    vpf_id: int, payload: VPFRecordUpdate, db: Session = Depends(get_db)
):
    return svc.update_vpf_record(db, vpf_id, payload)


@router.get("/uan", response_model=List[UANRecordResponse])
def list_uan(db: Session = Depends(get_db)):
    return svc.list_uan_records(db)


@router.post(
    "/uan",
    response_model=UANRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_uan(payload: UANRecordCreate, db: Session = Depends(get_db)):

    return svc.create_uan_record(db, payload)


@router.put("/uan/{uan_id}", response_model=UANRecordResponse)
def update_uan(
    uan_id: int, payload: UANRecordUpdate, db: Session = Depends(get_db)
):
    return svc.update_uan_record(db, uan_id, payload)


@router.post("/uan/{uan_id}/activate", response_model=UANRecordResponse)
def activate_uan(uan_id: int, db: Session = Depends(get_db)):

    return svc.activate_uan(db, uan_id)