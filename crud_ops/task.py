from sqlalchemy.orm import Session

from model.task import Task
from schema.task import TaskCreate, TaskUpdate
from utils.time_utils import to_total_minutes


def create_task(db: Session, task_in: TaskCreate):
    total_minutes = to_total_minutes(
        days=task_in.projected_days,
        hours=task_in.projected_hours,
        minutes=task_in.projected_minutes,
    )

    db_obj = Task(
        name=task_in.name,
        description=task_in.description,
        start_date=task_in.start_date,
        end_date=task_in.end_date,
        projected_minutes=total_minutes,
        completed=task_in.completed or False,
    )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


def get_task(db: Session, task_id: int):
    return db.query(Task).filter(Task.id == task_id).first()


def list_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Task).offset(skip).limit(limit).all()


def update_task(db: Session, db_obj: Task, task_in: TaskUpdate):
    if task_in.name is not None:
        db_obj.name = task_in.name

    if task_in.description is not None:
        db_obj.description = task_in.description

    if task_in.start_date is not None:
        db_obj.start_date = task_in.start_date

    if task_in.end_date is not None:
        db_obj.end_date = task_in.end_date

    if any([task_in.projected_days, task_in.projected_hours, task_in.projected_minutes]):
        db_obj.projected_minutes = to_total_minutes(
            task_in.projected_days or 0,
            task_in.projected_hours or 0,
            task_in.projected_minutes or 0,
        )

    if task_in.completed is not None:
        db_obj.completed = task_in.completed

    db.commit()
    db.refresh(db_obj)
    return db_obj


def delete_task(db: Session, task_id: int):
    obj = get_task(db, task_id)
    if obj:
        db.delete(obj)
        db.commit()
    return obj
