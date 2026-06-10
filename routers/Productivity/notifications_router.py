from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date

from core.database import get_db
from model.Productivity.notification import ProductivityNotification  # Model
from schema.Productivity.projects import NotificationCreate, Notification as NotificationSchema  # Schema

router = APIRouter(prefix="/notificationmanagement")


# CREATE
@router.post("/", response_model=NotificationSchema)
def create_notification(note: NotificationCreate, db: Session = Depends(get_db)):
    new_note = ProductivityNotification(
        message=note.message,
        is_read=False,
        created_at=date.today()
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note



@router.get("/", response_model=list[NotificationSchema])
def get_notifications(db: Session = Depends(get_db)):
    return db.query(ProductivityNotification).all()



@router.put("/{notification_id}", response_model=NotificationSchema)
def update_notification(notification_id: int, request: NotificationCreate, db: Session = Depends(get_db)):
    ProductivityNotification = db.query(ProductivityNotification).filter(ProductivityNotification.id == notification_id).first()
    if not ProductivityNotification:
        raise HTTPException(status_code=404, detail="ProductivityNotification not found")

    ProductivityNotification.message = request.message
    db.commit()
    db.refresh(ProductivityNotification)
    return ProductivityNotification



@router.delete("/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    ProductivityNotification = db.query(ProductivityNotification).filter(ProductivityNotification.id == notification_id).first()
    if not ProductivityNotification:
        raise HTTPException(status_code=404, detail="ProductivityNotification not found")

    db.delete(ProductivityNotification)
    db.commit()
    return {"message": "ProductivityNotification deleted successfully"}
