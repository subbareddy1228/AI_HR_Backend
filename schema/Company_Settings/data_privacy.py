

from __future__ import annotations
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, field_validator, HttpUrl



class ConsentSettings(BaseModel):
    marketing:           bool = True
    data_sharing:        bool = True
    analytics:           bool = True
    third_party:         bool = True
    profiling:           bool = False
    automated_decisions: bool = False



class DataPrivacyCreate(BaseModel):
   
    data_retention_period_years:    int     = 7
    inactive_account_period_days:   int     = 365


    auto_delete_inactive_accounts:   bool = True
    gdpr_compliance_enabled:         bool = True
    require_data_processing_consent: bool = True
    allow_data_export:               bool = True
    enable_data_anonymization:       bool = False

   
    consent: ConsentSettings = ConsentSettings()

   
    privacy_policy_version: str             = "1.0"
    last_consent_update:    Optional[date]  = None
    privacy_policy_url:     Optional[str]   = None

    @field_validator("data_retention_period_years")
    @classmethod
    def retention_range(cls, v):
        if v < 1 or v > 99:
            raise ValueError("data_retention_period_years must be between 1 and 99")
        return v

    @field_validator("inactive_account_period_days")
    @classmethod
    def inactive_range(cls, v):
        if v < 1 or v > 3650:
            raise ValueError("inactive_account_period_days must be between 1 and 3650")
        return v


class DataPrivacyUpdate(DataPrivacyCreate):
    """All fields optional for PATCH semantics."""
    data_retention_period_years:    Optional[int]  = None
    inactive_account_period_days:   Optional[int]  = None
    auto_delete_inactive_accounts:   Optional[bool] = None
    gdpr_compliance_enabled:         Optional[bool] = None
    require_data_processing_consent: Optional[bool] = None
    allow_data_export:               Optional[bool] = None
    enable_data_anonymization:       Optional[bool] = None
    consent:                         Optional[ConsentSettings] = None
    privacy_policy_version:          Optional[str]  = None
    last_consent_update:             Optional[date] = None
    privacy_policy_url:              Optional[str]  = None



class DataPrivacyResponse(BaseModel):
    id:                             int
    tenant_id:                      int

    data_retention_period_years:    int
    inactive_account_period_days:   int
    auto_delete_inactive_accounts:  bool
    gdpr_compliance_enabled:        bool
    require_data_processing_consent: bool
    allow_data_export:              bool
    enable_data_anonymization:      bool

  
    consent_marketing:           bool
    consent_data_sharing:        bool
    consent_analytics:           bool
    consent_third_party:         bool
    consent_profiling:           bool
    consent_automated_decisions: bool

    privacy_policy_version: str
    last_consent_update:    Optional[date]  = None
    privacy_policy_url:     Optional[str]   = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
