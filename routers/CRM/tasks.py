from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from crud_ops.task import (create_task,list_tasks,get_task,update_task,delete_task)
from schema.task import Task, TaskCreate, TaskUpdate
from core.session import get_db

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=Task, status_code=201)
def create_task_route(task_in: TaskCreate, db: Session = Depends(get_db)):
    return create_task(db, task_in)


@router.get("/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return list_tasks(db, skip, limit)


@router.get("/{task_id}", response_model=Task)
def read_task(task_id: int, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/{task_id}", response_model=Task)
def update_task_route(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return update_task(db, task, task_in)


@router.delete("/{task_id}", response_model=Task)
def delete_task_route(task_id: int, db: Session = Depends(get_db)):
    task = delete_task(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task
