from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import model.models
from schema import schemas
from core.database import get_db

router = APIRouter()

# Create a new task
@router.post("/", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = model.models.Task(
        title=task.title,
        description=task.description,
        assignee=task.assignee,
        due_date=task.due_date,
        status=task.status
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

# Get all tasks
@router.get("/", response_model=List[schemas.TaskOut])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(model.models.Task).all()

# Get task by ID
@router.get("/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(model.models.Task).filter(model.models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# Update task
@router.put("/{task_id}", response_model=schemas.TaskOut)
def update_task(task_id: int, task_update: schemas.TaskUpdate, db: Session = Depends(get_db)):
    task = db.query(model.models.Task).filter(model.models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task

# Delete task
@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(model.models.Task).filter(model.models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return {"message": "Task deleted"}

# Task progress
@router.get("/progress")
def get_progress(
    assignee: Optional[str] = Query(None, description="Filter by assignee"),
    db: Session = Depends(get_db)
):
    if assignee:
        tasks = db.query(model.models.Task).filter(model.models.Task.assignee == assignee).all()
        label = assignee
    else:
        tasks = db.query(model.models.Task).all()
        label = "all"

    if not tasks:
        return {"assignee": label, "progress": 0, "total_tasks": 0, "completed_tasks": 0}

    completed = len([t for t in tasks if t.status.lower() in ["done", "completed"]])
    progress = int((completed / len(tasks)) * 100)

    return {
        "assignee": label,
        "progress": progress,
        "total_tasks": len(tasks),
        "completed_tasks": completed
    }
