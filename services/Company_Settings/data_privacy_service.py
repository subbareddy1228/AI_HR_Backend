

from __future__ import annotations
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from model.Company_Settings.data_privacy import DataPrivacySetting
from schema.Company_Settings.data_privacy import DataPrivacyCreate, DataPrivacyUpdate


def upsert_data_privacy(
    db:        Session,
    tenant_id: int,
    data:      DataPrivacyCreate,
    actor_id:  Optional[int] = None,
) -> DataPrivacySetting:
    """
    Create or update data privacy settings (one record per tenant).
    Consent nested model is flattened into DB columns.
    """
    setting = _get_setting(db, tenant_id)

    flat = {
        "data_retention_period_years":    data.data_retention_period_years,
        "inactive_account_period_days":   data.inactive_account_period_days,
        "auto_delete_inactive_accounts":  data.auto_delete_inactive_accounts,
        "gdpr_compliance_enabled":        data.gdpr_compliance_enabled,
        "require_data_processing_consent": data.require_data_processing_consent,
        "allow_data_export":              data.allow_data_export,
        "enable_data_anonymization":      data.enable_data_anonymization,
        "privacy_policy_version":         data.privacy_policy_version,
        "last_consent_update":            data.last_consent_update,
        "privacy_policy_url":             data.privacy_policy_url,
    }

    if data.consent:
        flat.update({
            "consent_marketing":           data.consent.marketing,
            "consent_data_sharing":        data.consent.data_sharing,
            "consent_analytics":           data.consent.analytics,
            "consent_third_party":         data.consent.third_party,
            "consent_profiling":           data.consent.profiling,
            "consent_automated_decisions": data.consent.automated_decisions,
        })

    if setting:
        for field, value in flat.items():
            if value is not None:
                setattr(setting, field, value)
        setting.updated_by = actor_id
    else:
        setting = DataPrivacySetting(
            tenant_id  = tenant_id,
            updated_by = actor_id,
            **{k: v for k, v in flat.items() if v is not None},
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


def get_data_privacy(db: Session, tenant_id: int) -> DataPrivacySetting:
    setting = _get_setting(db, tenant_id)
    if not setting:
        raise HTTPException(
            status_code=404,
            detail="Data privacy settings not configured",
        )
    return setting



def _get_setting(db: Session, tenant_id: int) -> Optional[DataPrivacySetting]:
    return (
        db.query(DataPrivacySetting)
        .filter(DataPrivacySetting.tenant_id == tenant_id)
        .first()
    )
