

from __future__ import annotations
import os
import time
import logging
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from datetime import datetime

from model.Company_Settings.policy import Policy
from schema.Company_Settings.policy import PolicyCreate, PolicyUpdate

logger = logging.getLogger(__name__)

UPLOAD_DIR          = "uploads/policies"
ALLOWED_EXTENSIONS  = {".pdf", ".doc", ".docx", ".xlsx", ".ppt", ".pptx"}
MAX_SIZE_BYTES      = 20 * 1024 * 1024  # 20 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _save_document(file: UploadFile) -> tuple[str, str, int]:
   
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document format. Allowed: {ALLOWED_EXTENSIONS}",
        )

    contents = file.file.read()
    if len(contents) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Document exceeds 20 MB limit",
        )

    filename = f"{int(time.time() * 1000)}_{file.filename}"
    path     = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(contents)

    logger.info("Policy document saved → %s (%d bytes)", path, len(contents))
    return path, file.filename, len(contents)


def _delete_document_file(path: Optional[str]) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError as exc:
            logger.warning("Could not delete old document %s: %s", path, exc)


def get_all_policies(
    db:        Session,
    tenant_id: int,
    category:  Optional[str] = None,
    status:    Optional[str] = None,
) -> List[Policy]:
    q = db.query(Policy).filter(
        Policy.tenant_id == tenant_id,
        Policy.is_deleted.is_(False),
    )
    if category:
        q = q.filter(Policy.category == category)
    if status:
        q = q.filter(Policy.status == status)
    return q.order_by(Policy.updated_at.desc()).all()


def get_policy(db: Session, tenant_id: int, policy_id: int) -> Policy:
    return _get_or_404(db, tenant_id, policy_id)


def create_policy(
    db:        Session,
    tenant_id: int,
    data:      PolicyCreate,
    document:  Optional[UploadFile] = None,
    actor_id:  Optional[int]        = None,
) -> Policy:
    doc_path = doc_name = doc_size = None
    if document and document.filename:
        doc_path, doc_name, doc_size = _save_document(document)

    policy = Policy(
        tenant_id              = tenant_id,
        document_path          = doc_path,
        document_original_name = doc_name,
        document_size_bytes    = doc_size,
        status                 = "Active",
        updated_by             = actor_id,
        **data.model_dump(),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(
    db:        Session,
    tenant_id: int,
    policy_id: int,
    data:      PolicyUpdate,
    document:  Optional[UploadFile] = None,
    actor_id:  Optional[int]        = None,
) -> Policy:
    policy = _get_or_404(db, tenant_id, policy_id)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(policy, field, value)

    if document and document.filename:
        _delete_document_file(policy.document_path)
        policy.document_path, policy.document_original_name, policy.document_size_bytes = (
            _save_document(document)
        )

    policy.updated_by = actor_id
    db.commit()
    db.refresh(policy)
    return policy


def delete_policy(
    db: Session, tenant_id: int, policy_id: int, actor_id: Optional[int] = None
) -> None:
  
    policy = _get_or_404(db, tenant_id, policy_id)
    policy.is_deleted  = True
    policy.deleted_at  = datetime.utcnow()
    policy.updated_by  = actor_id
    db.commit()


def download_policy_document(db: Session, tenant_id: int, policy_id: int) -> str:

    policy = _get_or_404(db, tenant_id, policy_id)
    if not policy.document_path or not os.path.exists(policy.document_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    return policy.document_path


def _get_or_404(db: Session, tenant_id: int, policy_id: int) -> Policy:
    policy = (
        db.query(Policy)
        .filter(
            Policy.id        == policy_id,
            Policy.tenant_id == tenant_id,
            Policy.is_deleted.is_(False),
        )
        .first()
    )
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
