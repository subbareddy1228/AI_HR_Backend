from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from schema import activity
from crud_ops import crud
from core.database import get_db

router = APIRouter()

# Get all activities
@router.get("/", response_model=list[activity.Activity])
def read_activities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    try:
        activities = crud.get_activities(db, skip=skip, limit=limit)
        return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a new activity
@router.post("/", response_model=activity.Activity)
def create_activity(activity: activity.ActivityCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_activity(db, activity)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get a single activity by ID
@router.get("/{activity_id}", response_model=activity.Activity)
def read_activity(activity_id: int, db: Session = Depends(get_db)):
    db_activity = crud.get_activity(db, activity_id)
    if not db_activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return db_activity

# Update an activity
@router.put("/{activity_id}", response_model=activity.Activity)
def update_activity(activity_id: int, activity: activity.ActivityUpdate, db: Session = Depends(get_db)):
    try:
        updated_activity = crud.update_activity(db, activity_id, activity)
        if not updated_activity:
            raise HTTPException(status_code=404, detail="Activity not found")
        return updated_activity
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Delete an activity
@router.delete("/{activity_id}")
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    try:
        success = crud.delete_activity(db, activity_id)
        if not success:
            raise HTTPException(status_code=404, detail="Activity not found")
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
