from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

from core.database import Base, get_db



class CompanySettingsAdmin(Base):
    __tablename__ = "company_settings_admin"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(20), nullable=True, default="#1E40AF")
    secondary_color = Column(String(20), nullable=True, default="#64748B")
    default_currency = Column(String(10), default="INR")
    default_timezone = Column(String(50), default="Asia/Kolkata")
    default_language = Column(String(20), default="en")
    payroll_cycle = Column(String(20), default="MONTHLY")          # MONTHLY | BIWEEKLY | WEEKLY
    financial_year_start = Column(String(5), default="04-01")      # MM-DD format
    modules_enabled = Column(JSON, nullable=True)                  # {"payroll": true, "attendance": true}
    support_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class CompanySettingsCreate(BaseModel):
    company_name: str
    logo_url: Optional[str] = None
    primary_color: Optional[str] = "#1E40AF"
    secondary_color: Optional[str] = "#64748B"
    default_currency: Optional[str] = "INR"
    default_timezone: Optional[str] = "Asia/Kolkata"
    default_language: Optional[str] = "en"
    payroll_cycle: Optional[str] = "MONTHLY"
    financial_year_start: Optional[str] = "04-01"
    modules_enabled: Optional[dict] = None
    support_email: Optional[str] = None


class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    default_currency: Optional[str] = None
    default_timezone: Optional[str] = None
    default_language: Optional[str] = None
    payroll_cycle: Optional[str] = None
    financial_year_start: Optional[str] = None
    modules_enabled: Optional[dict] = None
    support_email: Optional[str] = None
    is_active: Optional[bool] = None


class CompanySettingsResponse(BaseModel):
    id: int
    company_name: str
    logo_url: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    default_currency: str
    default_timezone: str
    default_language: str
    payroll_cycle: str
    financial_year_start: str
    modules_enabled: Optional[dict]
    support_email: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



router = APIRouter(prefix="/company-settings", tags=["Super Admin"])


@router.post("/", response_model=CompanySettingsResponse, status_code=201)
def create_settings(payload: CompanySettingsCreate, db: Session = Depends(get_db)):
    settings = CompanySettingsAdmin(**payload.model_dump())
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/", response_model=List[CompanySettingsResponse])
def list_settings(db: Session = Depends(get_db)):
    return db.query(CompanySettingsAdmin).filter(CompanySettingsAdmin.is_active == True).all()


@router.get("/{settings_id}", response_model=CompanySettingsResponse)
def get_settings(settings_id: int, db: Session = Depends(get_db)):
    settings = db.query(CompanySettingsAdmin).filter(CompanySettingsAdmin.id == settings_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Company settings not found")
    return settings


@router.patch("/{settings_id}", response_model=CompanySettingsResponse)
def update_settings(settings_id: int, payload: CompanySettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(CompanySettingsAdmin).filter(CompanySettingsAdmin.id == settings_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Company settings not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


@router.delete("/{settings_id}")
def delete_settings(settings_id: int, db: Session = Depends(get_db)):
    settings = db.query(CompanySettingsAdmin).filter(CompanySettingsAdmin.id == settings_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Company settings not found")
    db.delete(settings)
    db.commit()
    return {"message": "Company settings deleted successfully"}
