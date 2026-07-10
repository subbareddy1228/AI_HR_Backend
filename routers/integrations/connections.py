from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
import model.models

router = APIRouter(prefix="/integrations", tags=["Integrations"])

# Fixed catalog — description/name lives here since it's static reference
# data, not something that needs to round-trip through the DB.
CATALOG = {
    "slack": {"name": "Slack", "description": "Get real-time notifications for new applications, interview schedules, and hiring updates."},
    "gmail": {"name": "Gmail", "description": "Send candidate emails, interview invites, and offer letters directly from Gmail."},
    "google-calendar": {"name": "Google Calendar", "description": "Sync interview schedules automatically with your Google Calendar."},
}


class IntegrationOut(BaseModel):
    id: str
    name: str
    description: str
    status: str
    connected_at: Optional[str] = None


def _row_to_out(integration_id: str, row: Optional["model.models.IntegrationConnection"]) -> IntegrationOut:
    meta = CATALOG[integration_id]
    return IntegrationOut(
        id=integration_id,
        name=meta["name"],
        description=meta["description"],
        status=row.status if row else "disconnected",
        connected_at=row.connected_at.isoformat() if row and row.connected_at else None,
    )


@router.get("/", response_model=List[IntegrationOut])
def list_integrations(db: Session = Depends(get_db)):
    rows = {r.integration_id: r for r in db.query(model.models.IntegrationConnection).all()}
    return [_row_to_out(iid, rows.get(iid)) for iid in CATALOG]


@router.post("/{integration_id}/connect", response_model=IntegrationOut)
def connect_integration(integration_id: str, db: Session = Depends(get_db)):
    """
    NOTE: this does not perform a real OAuth handshake with Slack/Gmail/
    Google Calendar — there is no app registration for any of them in this
    backend. It only records that an admin turned this on, so the toggle
    state survives a page reload instead of being purely client-side fake
    state. Wire a real OAuth flow before treating this as actually connected.
    """
    if integration_id not in CATALOG:
        integration_id = integration_id  # unknown ids are still recorded, just won't have catalog metadata beyond id

    row = db.query(model.models.IntegrationConnection).filter(
        model.models.IntegrationConnection.integration_id == integration_id
    ).first()
    if not row:
        row = model.models.IntegrationConnection(integration_id=integration_id)
        db.add(row)

    row.status = "connected"
    row.connected_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return _row_to_out(integration_id, row)


@router.post("/{integration_id}/disconnect", response_model=IntegrationOut)
def disconnect_integration(integration_id: str, db: Session = Depends(get_db)):
    row = db.query(model.models.IntegrationConnection).filter(
        model.models.IntegrationConnection.integration_id == integration_id
    ).first()
    if row:
        row.status = "disconnected"
        row.connected_at = None
        db.commit()
        db.refresh(row)
    return _row_to_out(integration_id, row)