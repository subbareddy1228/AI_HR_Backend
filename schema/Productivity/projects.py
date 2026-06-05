from pydantic import BaseModel
from datetime import date

class ProjectBase(BaseModel):
    name: str
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = "Active"

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None

class Project(ProjectBase):
    id: int
    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    status: str | None = "Pending"
    due_date: date | None = None


class TaskCreate(TaskBase):
    project_id: int
    team_id: int | None = None
    assigned_to: int | None = None

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    project_id: int | None = None
    team_id: int | None = None
    assigned_to: int | None = None
    status: str | None = None
    due_date: date | None = None


class Task(TaskBase):
    id: int
    project_id: int
    team_id: int | None
    assigned_to: int | None

    class Config:
        from_attributes = True


class NotificationBase(BaseModel):
    message: str
    is_read: bool | None = False

class NotificationCreate(NotificationBase):
    pass

class Notification(NotificationBase):
    id: int
    class Config:
        from_attributes = True
