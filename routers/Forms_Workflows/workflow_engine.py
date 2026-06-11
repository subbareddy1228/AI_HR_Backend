
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from core.database import get_db
from schema.Forms_Workflows.workflow_engine import (
    AutoApprovalRuleCreate,
    AutoApprovalRuleResponse,
    AutoApprovalRuleUpdate,
    EscalationConfigCreate,
    EscalationConfigResponse,
    EscalationConfigUpdate,
    EscalationRuleCreate,
    EscalationRuleResponse,
    EscalationRuleUpdate,
    IntegrationTestResponse,
    StageActionPayload,
    WorkflowActionsConfigCreate,
    WorkflowActionsConfigResponse,
    WorkflowActionsConfigUpdate,
    WorkflowApproverCreate,
    WorkflowApproverResponse,
    WorkflowApproverUpdate,
    WorkflowConfigCreate,
    WorkflowConfigResponse,
    WorkflowConfigSummary,
    WorkflowConfigUpdate,
    WorkflowEngineInstanceCreate,
    WorkflowEngineInstanceResponse,
    WorkflowIntegrationConfigCreate,
    WorkflowIntegrationConfigResponse,
    WorkflowIntegrationConfigUpdate,
    WorkflowPreviewResponse,
    WorkflowStageCreate,
    WorkflowStageResponse,
    WorkflowStageUpdate,
    WorkflowValidationResult,
)
from services.Forms_Workflows.workflow_engine_service import (
    ActionsConfigService,
    ApproverService,
    AutoApprovalRuleService,
    EscalationService,
    IntegrationConfigService,
    StageService,
    WorkflowConfigService,
    WorkflowEngineService,
)

router = APIRouter(prefix="/workflows", tags=["Forms & Workflows – Workflow Engine"])


def _handle(fn):
   
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return wrapper


@router.post(
    "/",
    response_model=WorkflowConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create workflow with optional nested stages / rules / configs",
)
@_handle
def create_workflow(
    payload: WorkflowConfigCreate,
    request: Request,
    db: Session = Depends(get_db),
):
    created_by = request.headers.get("X-User-Id")
    return WorkflowConfigService.create(db, payload, created_by)


@router.get(
    "/",
    response_model=List[WorkflowConfigSummary],
    summary="List all workflows (summary)",
)
def list_workflows(
    status_filter: Optional[str] = Query(None, alias="status"),
    reference_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    workflows = WorkflowConfigService.list_all(db, status_filter, reference_type)
    return [
        WorkflowConfigSummary(
            id            = wf.id,
            workflow_name = wf.workflow_name,
            workflow_type = wf.workflow_type,
            status        = wf.status,
            stage_count   = len(wf.stages),
            created_at    = wf.created_at,
        )
        for wf in workflows
    ]


@router.get(
    "/{workflow_id}",
    response_model=WorkflowConfigResponse,
    summary="Get workflow with all nested configurations",
)
@_handle
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = WorkflowConfigService.get_by_id(db, workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found.")
    return wf


@router.put(
    "/{workflow_id}",
    response_model=WorkflowConfigResponse,
    summary="Update top-level workflow metadata",
)
@_handle
def update_workflow(
    workflow_id: int,
    payload: WorkflowConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    updated_by = request.headers.get("X-User-Id")
    return WorkflowConfigService.update(db, workflow_id, payload, updated_by)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workflow and all its sub-configurations",
)
@_handle
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    WorkflowConfigService.delete(db, workflow_id)


@router.patch(
    "/{workflow_id}/disable",
    response_model=WorkflowConfigResponse,
    summary="Disable Workflow (Disable Workflow button)",
)
@_handle
def disable_workflow(
    workflow_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    updated_by = request.headers.get("X-User-Id")
    return WorkflowConfigService.disable(db, workflow_id, updated_by)


@router.get(
    "/{workflow_id}/validate",
    response_model=WorkflowValidationResult,
    summary="Validate workflow completeness (Validate button)",
)
@_handle
def validate_workflow(workflow_id: int, db: Session = Depends(get_db)):
    return WorkflowConfigService.validate(db, workflow_id)


@router.get(
    "/{workflow_id}/preview",
    response_model=WorkflowPreviewResponse,
    summary="Preview workflow structure (Preview Workflow button)",
)
@_handle
def preview_workflow(workflow_id: int, db: Session = Depends(get_db)):
    return WorkflowConfigService.preview(db, workflow_id)


@router.post(
    "/{workflow_id}/clone",
    response_model=WorkflowConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone workflow as template (Save as Template button)",
)
@_handle
def clone_workflow_as_template(
    workflow_id: int,
    new_name: str = Query(..., description="Name for the cloned template"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    created_by = request.headers.get("X-User-Id") if request else None
    return WorkflowConfigService.clone_as_template(db, workflow_id, new_name, created_by)


@router.post(
    "/{workflow_id}/stages",
    response_model=WorkflowStageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Stage (+ Add Stage button)",
)
@_handle
def add_stage(
    workflow_id: int,
    payload: WorkflowStageCreate,
    db: Session = Depends(get_db),
):
    db.flush   # ensure workflow exists
    stage = StageService.create(db, workflow_id, payload)
    db.commit()
    db.refresh(stage)
    return stage


@router.put(
    "/{workflow_id}/stages/{stage_id}",
    response_model=WorkflowStageResponse,
    summary="Edit stage (Edit button)",
)
@_handle
def update_stage(
    workflow_id: int,
    stage_id: int,
    payload: WorkflowStageUpdate,
    db: Session = Depends(get_db),
):
    return StageService.update(db, stage_id, payload)


@router.delete(
    "/{workflow_id}/stages/{stage_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete stage",
)
@_handle
def delete_stage(workflow_id: int, stage_id: int, db: Session = Depends(get_db)):
    StageService.delete(db, stage_id)


@router.post(
    "/stages/{stage_id}/approvers",
    response_model=WorkflowApproverResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Approver (Add Approver button)",
)
@_handle
def add_approver(
    stage_id: int,
    payload: WorkflowApproverCreate,
    db: Session = Depends(get_db),
):
    return ApproverService.add(db, stage_id, payload)


@router.put(
    "/approvers/{approver_id}",
    response_model=WorkflowApproverResponse,
    summary="Update an approver",
)
@_handle
def update_approver(
    approver_id: int,
    payload: WorkflowApproverUpdate,
    db: Session = Depends(get_db),
):
    return ApproverService.update(db, approver_id, payload)


@router.delete(
    "/approvers/{approver_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an approver from a stage",
)
@_handle
def delete_approver(approver_id: int, db: Session = Depends(get_db)):
    ApproverService.delete(db, approver_id)


@router.get(
    "/{workflow_id}/auto-approval-rules",
    response_model=List[AutoApprovalRuleResponse],
    summary="List auto-approval rules",
)
@_handle
def list_auto_rules(workflow_id: int, db: Session = Depends(get_db)):
    wf = WorkflowConfigService.get_by_id(db, workflow_id)
    if not wf:
        raise HTTPException(404, detail=f"Workflow {workflow_id} not found.")
    return wf.auto_approval_rules


@router.post(
    "/{workflow_id}/auto-approval-rules",
    response_model=AutoApprovalRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add auto-approval rule (+ Add Rule button)",
)
@_handle
def add_auto_rule(
    workflow_id: int,
    payload: AutoApprovalRuleCreate,
    db: Session = Depends(get_db),
):
    rule = AutoApprovalRuleService.create(db, workflow_id, payload)
    db.commit()
    db.refresh(rule)
    return rule


@router.put(
    "/auto-approval-rules/{rule_id}",
    response_model=AutoApprovalRuleResponse,
    summary="Update auto-approval rule",
)
@_handle
def update_auto_rule(
    rule_id: int,
    payload: AutoApprovalRuleUpdate,
    db: Session = Depends(get_db),
):
    return AutoApprovalRuleService.update(db, rule_id, payload)


@router.delete(
    "/auto-approval-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete auto-approval rule",
)
@_handle
def delete_auto_rule(rule_id: int, db: Session = Depends(get_db)):
    AutoApprovalRuleService.delete(db, rule_id)



@router.get(
    "/{workflow_id}/escalation",
    response_model=EscalationConfigResponse,
    summary="Get escalation configuration",
)
@_handle
def get_escalation(workflow_id: int, db: Session = Depends(get_db)):
    wf = WorkflowConfigService.get_by_id(db, workflow_id)
    if not wf:
        raise HTTPException(404, detail=f"Workflow {workflow_id} not found.")
    if not wf.escalation_config:
        raise HTTPException(404, detail="No escalation config for this workflow.")
    return wf.escalation_config


@router.post(
    "/{workflow_id}/escalation",
    response_model=EscalationConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace escalation configuration",
)
@_handle
def upsert_escalation(
    workflow_id: int,
    payload: EscalationConfigCreate,
    db: Session = Depends(get_db),
):
    return EscalationService.create_or_update_config(db, workflow_id, payload)


@router.patch(
    "/{workflow_id}/escalation",
    response_model=EscalationConfigResponse,
    summary="Partially update escalation settings",
)
@_handle
def patch_escalation(
    workflow_id: int,
    payload: EscalationConfigUpdate,
    db: Session = Depends(get_db),
):
    return EscalationService.update_config(db, workflow_id, payload)



@router.post(
    "/{workflow_id}/escalation/rules",
    response_model=EscalationRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add escalation rule (+ Add Rule button)",
)
@_handle
def add_escalation_rule(
    workflow_id: int,
    payload: EscalationRuleCreate,
    db: Session = Depends(get_db),
):
    wf = WorkflowConfigService.get_by_id(db, workflow_id)
    if not wf or not wf.escalation_config:
        raise HTTPException(404, detail="Escalation config not found. Create it first.")
    return EscalationService.add_rule(db, wf.escalation_config.id, payload)


@router.put(
    "/escalation/rules/{rule_id}",
    response_model=EscalationRuleResponse,
    summary="Update escalation rule (Edit / pencil icon)",
)
@_handle
def update_escalation_rule(
    rule_id: int,
    payload: EscalationRuleUpdate,
    db: Session = Depends(get_db),
):
    return EscalationService.update_rule(db, rule_id, payload)


@router.delete(
    "/escalation/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete escalation rule (trash icon)",
)
@_handle
def delete_escalation_rule(rule_id: int, db: Session = Depends(get_db)):
    EscalationService.delete_rule(db, rule_id)


@router.get(
    "/{workflow_id}/actions",
    response_model=WorkflowActionsConfigResponse,
    summary="Get workflow actions configuration",
)
@_handle
def get_actions_config(workflow_id: int, db: Session = Depends(get_db)):
    wf = WorkflowConfigService.get_by_id(db, workflow_id)
    if not wf:
        raise HTTPException(404, detail=f"Workflow {workflow_id} not found.")
    if not wf.actions_config:
        raise HTTPException(404, detail="No actions config for this workflow.")
    return wf.actions_config


@router.post(
    "/{workflow_id}/actions",
    response_model=WorkflowActionsConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace workflow actions configuration",
)
@_handle
def upsert_actions_config(
    workflow_id: int,
    payload: WorkflowActionsConfigCreate,
    db: Session = Depends(get_db),
):
    return ActionsConfigService.create_or_update(db, workflow_id, payload)


@router.patch(
    "/{workflow_id}/actions",
    response_model=WorkflowActionsConfigResponse,
    summary="Partially update actions configuration (checkbox toggles)",
)
@_handle
def patch_actions_config(
    workflow_id: int,
    payload: WorkflowActionsConfigUpdate,
    db: Session = Depends(get_db),
):
    return ActionsConfigService.update(db, workflow_id, payload)


@router.get(
    "/{workflow_id}/integration",
    response_model=WorkflowIntegrationConfigResponse,
    summary="Get integration configuration",
)
@_handle
def get_integration_config(workflow_id: int, db: Session = Depends(get_db)):
    wf = WorkflowConfigService.get_by_id(db, workflow_id)
    if not wf:
        raise HTTPException(404, detail=f"Workflow {workflow_id} not found.")
    if not wf.integration_config:
        raise HTTPException(404, detail="No integration config for this workflow.")
    return wf.integration_config


@router.post(
    "/{workflow_id}/integration",
    response_model=WorkflowIntegrationConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace integration configuration",
)
@_handle
def upsert_integration_config(
    workflow_id: int,
    payload: WorkflowIntegrationConfigCreate,
    db: Session = Depends(get_db),
):
    return IntegrationConfigService.create_or_update(db, workflow_id, payload)


@router.patch(
    "/{workflow_id}/integration",
    response_model=WorkflowIntegrationConfigResponse,
    summary="Partially update integration configuration (toggle systems on/off)",
)
@_handle
def patch_integration_config(
    workflow_id: int,
    payload: WorkflowIntegrationConfigUpdate,
    db: Session = Depends(get_db),
):
    return IntegrationConfigService.update(db, workflow_id, payload)


@router.post(
    "/{workflow_id}/integration/test",
    response_model=IntegrationTestResponse,
    summary="Test All Integrations button",
)
@_handle
def test_all_integrations(workflow_id: int, db: Session = Depends(get_db)):
    return IntegrationConfigService.run_integration_tests(db, workflow_id)


@router.get(
    "/{workflow_id}/integration/logs",
    summary="View Integration Logs button",
)
@_handle
def view_integration_logs(
    workflow_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    logs = IntegrationConfigService.get_integration_logs(db, workflow_id, limit)
    return [
        {
            "id":               log.id,
            "integration_key":  log.integration_key,
            "status":           log.status,
            "response_payload": log.response_payload,
            "error_message":    log.error_message,
            "tested_at":        log.tested_at.isoformat(),
        }
        for log in logs
    ]


@router.post(
    "/instances",
    response_model=WorkflowEngineInstanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a new workflow instance (triggers auto-approval evaluation)",
)
@_handle
def initiate_instance(
    payload: WorkflowEngineInstanceCreate,
    db: Session = Depends(get_db),
):
    return WorkflowEngineService.initiate(db, payload)


@router.get(
    "/instances",
    response_model=List[WorkflowEngineInstanceResponse],
    summary="List workflow instances with optional filters",
)
def list_instances(
    workflow_id:    Optional[int] = Query(None),
    status_filter:  Optional[str] = Query(None, alias="status"),
    reference_type: Optional[str] = Query(None),
    skip:           int           = Query(0, ge=0),
    limit:          int           = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return WorkflowEngineService.list_instances(
        db, workflow_id, status_filter, reference_type, skip, limit
    )


@router.get(
    "/instances/{instance_id}",
    response_model=WorkflowEngineInstanceResponse,
    summary="Get a workflow instance with full stage-log audit trail",
)
@_handle
def get_instance(instance_id: int, db: Session = Depends(get_db)):
    instance = WorkflowEngineService.get_instance(db, instance_id)
    if not instance:
        raise HTTPException(404, detail=f"Instance {instance_id} not found.")
    return instance


@router.post(
    "/instances/{instance_id}/action",
    response_model=WorkflowEngineInstanceResponse,
    summary="Approve / Reject / Send-back / Delegate / Request-info on an instance",
)
@_handle
def action_on_instance(
    instance_id: int,
    payload: StageActionPayload,
    db: Session = Depends(get_db),
):
    return WorkflowEngineService.apply_action(db, instance_id, payload)