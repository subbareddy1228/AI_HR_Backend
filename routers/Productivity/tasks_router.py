from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from model.Productivity.task import Task as TaskModel
from schema.Productivity.task import Task as TaskSchema, TaskCreate, TaskUpdate

router = APIRouter(prefix="/taskmanagement", tags=["Task Management"])



# GET ALL TASKS


@router.get("/", response_model=List[TaskSchema])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(TaskModel).all()



# CREATE TASK


@router.post("/", response_model=TaskSchema, status_code=status.HTTP_201_CREATED)
def create_task(request: TaskCreate, db: Session = Depends(get_db)):
    new_task = TaskModel(**request.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task



# UPDATE TASK (PATCH – GENERIC UPDATE)


@router.patch("/{task_id}", response_model=TaskSchema)
def update_task(
    task_id: int,
    request: TaskUpdate,
    db: Session = Depends(get_db)
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = request.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task



# COMPLETE TASK (EXPLICIT STATE CHANGE)


@router.post("/{task_id}/complete", response_model=TaskSchema)
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status == "Completed":
        raise HTTPException(
            status_code=400,
            detail="Task already completed"
        )

    task.status = "Completed"
    task.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(task)
    return task



# REOPEN TASK (OPTIONAL BUT REALISTIC)


@router.post("/{task_id}/reopen", response_model=TaskSchema)
def reopen_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "Pending"
    task.completed_at = None

    db.commit()
    db.refresh(task)
    return task



# DELETE TASK


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}
