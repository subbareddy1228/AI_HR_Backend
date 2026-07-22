
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from schema.Company_Settings.policy import (
    PolicyCreate,
    PolicyUpdate,
    PolicyResponse,
    PolicyListResponse,
)
from services.Company_Settings.policy_service import (
    get_all_policies,
    get_policy,
    create_policy,
    update_policy,
    delete_policy,
    download_policy_document,
)

router = APIRouter(
    prefix="/company-settings/policies",
    tags=["Company Settings – Policies"],
)


@router.get("/", response_model=PolicyListResponse)
def list_policies(
    category:     Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    policies = get_all_policies(db, current_user.tenant_id, category, status_filter)
    return PolicyListResponse(policies=policies, total=len(policies))


@router.get("/{policy_id}", response_model=PolicyResponse)
def read_policy(
    policy_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    return get_policy(db, current_user.tenant_id, policy_id)


@router.get("/{policy_id}/download")
def download_policy(
    policy_id:    int,
    current_user: User    = Depends(get_current_user),
    db:           Session = Depends(get_db),
):
    """Stream the policy document file for download."""
    policy  = get_policy(db, current_user.tenant_id, policy_id)
    path    = download_policy_document(db, current_user.tenant_id, policy_id)
    return FileResponse(
        path        = path,
        filename    = policy.document_original_name or "policy_document",
        media_type  = "application/octet-stream",
    )


@router.post("/", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def add_policy(
    title:          str           = Form(...),
    category:       str           = Form(...),
    version:        str           = Form(...),
    effective_date: str           = Form(...),
    description:    Optional[str] = Form(None),
    document:       Optional[UploadFile] = File(None),
    current_user:   User          = Depends(require_roles(["admin", "hr_admin"])),
    db:             Session       = Depends(get_db),
):
    from datetime import date
    data = PolicyCreate(
        title          = title,
        category       = category,
        version        = version,
        effective_date = date.fromisoformat(effective_date),
        description    = description,
    )
    return create_policy(db, current_user.tenant_id, data, document, current_user.id)


@router.put("/{policy_id}", response_model=PolicyResponse)
def edit_policy(
    policy_id:      int,
    title:          Optional[str] = Form(None),
    category:       Optional[str] = Form(None),
    version:        Optional[str] = Form(None),
    effective_date: Optional[str] = Form(None),
    description:    Optional[str] = Form(None),
    status:         Optional[str] = Form(None),
    document:       Optional[UploadFile] = File(None),
    current_user:   User          = Depends(require_roles(["admin", "hr_admin"])),
    db:             Session       = Depends(get_db),
):
    from datetime import date
    data = PolicyUpdate(
        title          = title,
        category       = category,
        version        = version,
        effective_date = date.fromisoformat(effective_date) if effective_date else None,
        description    = description,
        status         = status,
    )
    return update_policy(db, current_user.tenant_id, policy_id, data, document, current_user.id)


@router.delete("/{policy_id}", status_code=status.HTTP_200_OK)
def remove_policy(
    policy_id:    int,
    current_user: User    = Depends(require_roles(["admin", "hr_admin"])),
    db:           Session = Depends(get_db),
):
    delete_policy(db, current_user.tenant_id, policy_id, current_user.id)
