# app/crud.py
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session
from fastapi import HTTPException

import model



# CONTACT CRUD


def create_contact(db: Session, contact):
    if contact.email:
        existing = (
            db.query(model.Contact)
            .filter(model.Contact.email == contact.email)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

    db_contact = model.Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


def get_contacts(db: Session, skip: int = 0, limit: int = 50):
    return (
        db.query(model.Contact)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_contact(db: Session, contact_id: int):
    return (
        db.query(model.Contact)
        .filter(model.Contact.id == contact_id)
        .first()
    )


def update_contact(db: Session, contact_id: int, updated):
    db_contact = get_contact(db, contact_id)
    if not db_contact:
        return None

    update_data = updated.dict(exclude_unset=True)

    if "email" in update_data:
        existing = (
            db.query(model.Contact)
            .filter(
                model.Contact.email == update_data["email"],
                model.Contact.id != contact_id
            )
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

    for key, value in update_data.items():
        setattr(db_contact, key, value)

    db.commit()
    db.refresh(db_contact)
    return db_contact


def delete_contact(db: Session, contact_id: int) -> bool:
    db_contact = get_contact(db, contact_id)
    if not db_contact:
        return False

    db.delete(db_contact)
    db.commit()
    return True



# LEAD CRUD


def create_lead(db: Session, lead):
    db_lead = model.Lead(**lead.dict())
    db.add(db_lead)
    db.commit()
    db.refresh(db_lead)
    return db_lead


def get_leads(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(model.Lead)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_lead(db: Session, lead_id: int):
    return (
        db.query(model.Lead)
        .filter(model.Lead.id == lead_id)
        .first()
    )


def update_lead(db: Session, lead_id: int, updated):
    db_lead = get_lead(db, lead_id)
    if not db_lead:
        return None

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(db_lead, key, value)

    db_lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_lead)
    return db_lead


def delete_lead(db: Session, lead_id: int) -> bool:
    db_lead = get_lead(db, lead_id)
    if not db_lead:
        return False

    db.delete(db_lead)
    db.commit()
    return True



# PIPELINE CRUD


def create_pipeline(db: Session, pipeline):
    db_pipeline = model.Pipeline(**pipeline.dict())
    db.add(db_pipeline)
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline


def get_pipelines(db: Session):
    return db.query(model.Pipeline).all()


def get_pipeline(db: Session, pipeline_id: int):
    return (
        db.query(model.Pipeline)
        .filter(model.Pipeline.id == pipeline_id)
        .first()
    )


def update_pipeline(db: Session, pipeline_id: int, updated):
    db_pipeline = get_pipeline(db, pipeline_id)
    if not db_pipeline:
        return None

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(db_pipeline, key, value)

    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline


def delete_pipeline(db: Session, pipeline_id: int) -> bool:
    db_pipeline = get_pipeline(db, pipeline_id)
    if not db_pipeline:
        return False

    db.delete(db_pipeline)
    db.commit()
    return True



# ACTIVITY CRUD


def create_activity(db: Session, activity):
    db_activity = model.Activity(**activity.dict())
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity


def get_activities(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(model.Activity)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_activity(db: Session, activity_id: int):
    return (
        db.query(model.Activity)
        .filter(model.Activity.id == activity_id)
        .first()
    )


def delete_activity(db: Session, activity_id: int) -> bool:
    db_activity = get_activity(db, activity_id)
    if not db_activity:
        return False

    db.delete(db_activity)
    db.commit()
    return True

def update_activity(db: Session, activity_id: int, updated):
    db_activity = get_activity(db, activity_id)
    if not db_activity:
        return None

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(db_activity, key, value)

    # optional but recommended if column exists
    if hasattr(db_activity, "updated_at"):
        db_activity.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(db_activity)
    return db_activity

# LEAVE CRUD
from sqlalchemy.orm import Session
from model.models import LeaveRequest


def create_leave(db: Session, leave):
    db_leave = LeaveRequest(**leave.dict())
    db.add(db_leave)
    db.commit()
    db.refresh(db_leave)
    return db_leave


def get_leaves(db: Session):
    return db.query(LeaveRequest).all()


def get_leave_by_id(db: Session, leave_id: int):
    return (
        db.query(LeaveRequest)
        .filter(LeaveRequest.id == leave_id)
        .first()
    )
