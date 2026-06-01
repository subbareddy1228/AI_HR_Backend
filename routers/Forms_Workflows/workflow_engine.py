from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.database import get_db
from typing import Optional
from datetime import datetime

from model.Forms_Workflows.workflow import Workflow, WorkflowInstance
from schema.Forms_Workflows.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowResponse,
    WorkflowInstanceCreate,
    WorkflowInstanceUpdate,
    WorkflowInstanceResponse,
)

router = APIRouter(prefix="/workflows", tags=["Forms & Workflows"])


# ── Workflow definitions ───────────────────────────────────────────────────────

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    existing = db.execute(
        select(Workflow).where(Workflow.workflow_name == payload.workflow_name)
    ).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Workflow name already exists")
    wf = Workflow(**payload.model_dump())
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("/", response_model=list[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db)):
    return db.execute(select(Workflow)).scalars().all()


# ── Instances (defined before /{workflow_id} to avoid path conflict) ───────────

@router.post("/instances/", response_model=WorkflowInstanceResponse, status_code=status.HTTP_201_CREATED)
def create_instance(payload: WorkflowInstanceCreate, db: Session = Depends(get_db)):
    wf = db.execute(select(Workflow).where(Workflow.id == payload.workflow_id)).scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    instance = WorkflowInstance(**payload.model_dump())
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@router.get("/instances/", response_model=list[WorkflowInstanceResponse])
def list_instances(
    status: Optional[str] = Query(None),
    reference_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = select(WorkflowInstance)
    if status:
        query = query.where(WorkflowInstance.status == status)
    if reference_type:
        query = query.where(WorkflowInstance.reference_type == reference_type)
    return db.execute(query).scalars().all()


@router.get("/instances/{instance_id}", response_model=WorkflowInstanceResponse)
def get_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
    ).scalars().first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    return instance


@router.patch("/instances/{instance_id}/advance", response_model=WorkflowInstanceResponse)
def advance_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
    ).scalars().first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    if instance.status in ("Approved", "Rejected", "Cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot advance a {instance.status} workflow")
    instance.current_step += 1
    instance.status = "In Progress"
    db.commit()
    db.refresh(instance)
    return instance


@router.patch("/instances/{instance_id}/complete", response_model=WorkflowInstanceResponse)
def complete_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
    ).scalars().first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    instance.status = "Approved"
    instance.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(instance)
    return instance


@router.patch("/instances/{instance_id}/reject", response_model=WorkflowInstanceResponse)
def reject_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = db.execute(
        select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
    ).scalars().first()
    if not instance:
        raise HTTPException(status_code=404, detail="Workflow instance not found")
    instance.status = "Rejected"
    instance.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(instance)
    return instance


# ── Single workflow CRUD (after /instances/ routes) ───────────────────────────

@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.execute(select(Workflow).where(Workflow.id == workflow_id)).scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(workflow_id: int, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    wf = db.execute(select(Workflow).where(Workflow.id == workflow_id)).scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wf, field, value)
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.execute(select(Workflow).where(Workflow.id == workflow_id)).scalars().first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()
