from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from core.database import get_db
from model.Productivity.notification import Notification  # Model
from schema.Productivity.projects import NotificationCreate, Notification as NotificationSchema  # Schema

router = APIRouter(prefix="/notificationmanagement", tags=["Notification Management"])


# CREATE
@router.post("/", response_model=NotificationSchema)
def create_notification(note: NotificationCreate, db: Session = Depends(get_db)):
    new_note = Notification(
        message=note.message,
        is_read=False,
        created_at=date.today()
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note


# READ ALL
@router.get("/", response_model=list[NotificationSchema])
def get_notifications(db: Session = Depends(get_db)):
    return db.query(Notification).all()


# UPDATE
@router.put("/{notification_id}", response_model=NotificationSchema)
def update_notification(notification_id: int, request: NotificationCreate, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.message = request.message
    db.commit()
    db.refresh(notification)
    return notification


# DELETE
@router.delete("/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted successfully"}
