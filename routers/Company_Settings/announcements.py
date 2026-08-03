from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.dependencies import get_current_user, require_roles
from model.models import User
from model.Employee_Management.employee_self_service_extras import Announcement

router = APIRouter(prefix="/api/announcements", tags=["Announcements"])


class AnnouncementCreate(BaseModel):
    title: str
    body: str


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    body: str
    created_by_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[AnnouncementResponse])
def list_announcements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Every logged-in role can see announcements — this is deliberately
    NOT restricted to HR roles, since 'employee' needs to see these too."""
    query = db.query(Announcement).filter(Announcement.is_active.is_(True))
    if current_user.tenant_id is not None:
        query = query.filter(Announcement.tenant_id == current_user.tenant_id)
    return query.order_by(Announcement.created_at.desc()).all()


@router.post("/", response_model=AnnouncementResponse, status_code=201)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["hr_admin", "admin", "company", "superadmin"])),
):
    announcement = Announcement(
        tenant_id=current_user.tenant_id,
        title=payload.title,
        body=payload.body,
        created_by_name=current_user.name,
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["hr_admin", "admin", "company", "superadmin"])),
):
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    announcement.is_active = False
    db.commit()
    return {"message": "Announcement removed"}