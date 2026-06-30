

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select

from model.Forms_Workflows.workflow_engine import (
    AutoApprovalRule,
    EscalationConfiguration,
    EscalationRule,
    IntegrationTestLog,
    WorkflowActionsConfiguration,
    WorkflowApprover,
    WorkflowConfiguration,
    WorkflowEngineInstance,
    WorkflowIntegrationConfiguration,
    WorkflowStage,
    WorkflowStageLog,
    INTEGRATION_SYSTEM_CHOICES,
    InstanceStatusEnum,
)
from schema.Forms_Workflows.workflow_engine import (
    AutoApprovalRuleCreate,
    AutoApprovalRuleUpdate,
    EscalationConfigCreate,
    EscalationConfigUpdate,
    EscalationRuleCreate,
    EscalationRuleUpdate,
    IntegrationTestResultItem,
    IntegrationTestResponse,
    StageActionPayload,
    WorkflowActionsConfigCreate,
    WorkflowActionsConfigUpdate,
    WorkflowApproverCreate,
    WorkflowApproverUpdate,
    WorkflowConfigCreate,
    WorkflowConfigUpdate,
    WorkflowEngineInstanceCreate,
    WorkflowIntegrationConfigCreate,
    WorkflowIntegrationConfigUpdate,
    WorkflowPreviewResponse,
    WorkflowStageCreate,
    WorkflowStageUpdate,
    WorkflowValidationResult,
)


def _load_full_workflow(db: Session, workflow_id: int) -> Optional[WorkflowConfiguration]:

    return db.execute(
        select(WorkflowConfiguration)
        .options(
            selectinload(WorkflowConfiguration.stages)
            .selectinload(WorkflowStage.approvers),
            selectinload(WorkflowConfiguration.auto_approval_rules),
            selectinload(WorkflowConfiguration.escalation_config)
            .selectinload(EscalationConfiguration.rules),
            selectinload(WorkflowConfiguration.actions_config),
            selectinload(WorkflowConfiguration.integration_config),
        )
        .where(WorkflowConfiguration.id == workflow_id)
    ).scalars().first()


class WorkflowConfigService:


    @staticmethod
    def create(db: Session, payload: WorkflowConfigCreate,
               created_by: Optional[str] = None) -> WorkflowConfiguration:
        existing = db.execute(
            select(WorkflowConfiguration)
            .where(WorkflowConfiguration.workflow_name == payload.workflow_name)
        ).scalars().first()
        if existing:
            raise ValueError(f"Workflow '{payload.workflow_name}' already exists.")

        wf = WorkflowConfiguration(
            workflow_name        = payload.workflow_name,
            description          = payload.description,
            reference_type       = payload.reference_type,
            workflow_type        = payload.workflow_type,
            default_timeout      = payload.default_timeout,
            default_timeout_unit = payload.default_timeout_unit,
            status               = payload.status,
            is_template          = payload.is_template,
            created_by           = created_by,
            updated_by           = created_by,
        )
        db.add(wf)
        db.flush()  


        for i, stage_data in enumerate(payload.stages, start=1):
            StageService.create(db, wf.id, stage_data)


        for rule_data in payload.auto_approval_rules:
            AutoApprovalRuleService.create(db, wf.id, rule_data)


        if payload.escalation_config:
            EscalationService.create_or_update_config(db, wf.id, payload.escalation_config)


        if payload.actions_config:
            ActionsConfigService.create_or_update(db, wf.id, payload.actions_config)


        if payload.integration_config:
            IntegrationConfigService.create_or_update(db, wf.id, payload.integration_config)

        db.commit()
        return _load_full_workflow(db, wf.id)


    @staticmethod
    def get_by_id(db: Session, workflow_id: int) -> Optional[WorkflowConfiguration]:
        return _load_full_workflow(db, workflow_id)

    @staticmethod
    def list_all(db: Session,
                 status: Optional[str] = None,
                 reference_type: Optional[str] = None) -> List[WorkflowConfiguration]:
        q = select(WorkflowConfiguration).options(
            selectinload(WorkflowConfiguration.stages),
        )
        if status:
            q = q.where(WorkflowConfiguration.status == status)
        if reference_type:
            q = q.where(WorkflowConfiguration.reference_type == reference_type)
        return db.execute(q).scalars().all()


    @staticmethod
    def update(db: Session, workflow_id: int,
               payload: WorkflowConfigUpdate,
               updated_by: Optional[str] = None) -> WorkflowConfiguration:
        wf = _load_full_workflow(db, workflow_id)
        if not wf:
            raise LookupError(f"Workflow {workflow_id} not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(wf, field, value)
        wf.updated_by = updated_by
        wf.updated_at = datetime.utcnow()
        db.commit()
        return _load_full_workflow(db, workflow_id)


    @staticmethod
    def delete(db: Session, workflow_id: int) -> None:
        wf = db.get(WorkflowConfiguration, workflow_id)
        if not wf:
            raise LookupError(f"Workflow {workflow_id} not found.")
        db.delete(wf)
        db.commit()

    @staticmethod
    def disable(db: Session, workflow_id: int,
                updated_by: Optional[str] = None) -> WorkflowConfiguration:
        wf = db.get(WorkflowConfiguration, workflow_id)
        if not wf:
            raise LookupError(f"Workflow {workflow_id} not found.")
        wf.status = "disabled"
        wf.updated_by = updated_by
        wf.updated_at = datetime.utcnow()
        db.commit()
        return _load_full_workflow(db, workflow_id)


    @staticmethod
    def clone_as_template(db: Session, workflow_id: int,
                          new_name: str,
                          created_by: Optional[str] = None) -> WorkflowConfiguration:
        source = _load_full_workflow(db, workflow_id)
        if not source:
            raise LookupError(f"Workflow {workflow_id} not found.")

        create_payload = WorkflowConfigCreate(
            workflow_name        = new_name,
            description          = source.description,
            reference_type       = source.reference_type,
            workflow_type        = source.workflow_type,
            default_timeout      = source.default_timeout,
            default_timeout_unit = source.default_timeout_unit,
            status               = source.status,
            is_template          = True,
            stages=[
                WorkflowStageCreate(
                    stage_order  = s.stage_order,
                    stage_name   = s.stage_name,
                    timeout      = s.timeout,
                    timeout_unit = s.timeout_unit,
                    status       = s.status,
                    approvers=[
                        WorkflowApproverCreate(
                            approver_type = a.approver_type,
                            approver_ref  = a.approver_ref,
                            display_name  = a.display_name,
                            is_backup     = a.is_backup,
                        )
                        for a in s.approvers
                    ],
                )
                for s in source.stages
            ],
            auto_approval_rules=[
                AutoApprovalRuleCreate(
                    rule_order       = r.rule_order,
                    condition_field  = r.condition_field,
                    operator         = r.operator,
                    condition_value  = r.condition_value,
                    action           = r.action,
                    is_active        = r.is_active,
                )
                for r in source.auto_approval_rules
            ],
        )
        return WorkflowConfigService.create(db, create_payload, created_by)


    @staticmethod
    def validate(db: Session, workflow_id: int) -> WorkflowValidationResult:
        wf = _load_full_workflow(db, workflow_id)
        if not wf:
            return WorkflowValidationResult(is_valid=False,
                                            errors=[f"Workflow {workflow_id} not found."])
        errors:   List[str] = []
        warnings: List[str] = []

        if not wf.stages:
            errors.append("Workflow must have at least one stage.")
        else:
            for s in wf.stages:
                if not s.approvers:
                    warnings.append(f"Stage '{s.stage_name}' has no approvers assigned.")

        if not wf.escalation_config:
            warnings.append("No escalation configuration defined – timeout events will be unhandled.")

        if not wf.actions_config:
            warnings.append("No actions configuration – defaults will be used.")

        return WorkflowValidationResult(
            is_valid = len(errors) == 0,
            errors   = errors,
            warnings = warnings,
        )


    @staticmethod
    def preview(db: Session, workflow_id: int) -> WorkflowPreviewResponse:
        wf = _load_full_workflow(db, workflow_id)
        if not wf:
            raise LookupError(f"Workflow {workflow_id} not found.")

        stages_preview = [
            {
                "stage_order": s.stage_order,
                "stage_name":  s.stage_name,
                "timeout":     f"{s.timeout or wf.default_timeout} {(s.timeout_unit or wf.default_timeout_unit).value}",
                "status":      s.status.value,
                "approvers":   [{"ref": a.approver_ref, "type": a.approver_type} for a in s.approvers],
            }
            for s in sorted(wf.stages, key=lambda x: x.stage_order)
        ]

        auto_rules_preview = [
            {
                "rule_order":  r.rule_order,
                "condition":   f"{r.condition_field} {r.operator.value} {r.condition_value}",
                "action":      r.action.value,
                "is_active":   r.is_active,
            }
            for r in sorted(wf.auto_approval_rules, key=lambda x: x.rule_order)
        ]

        escalation_preview = None
        if wf.escalation_config:
            ec = wf.escalation_config
            escalation_preview = {
                "default_timeout": f"{ec.default_escalation_time} {ec.default_escalation_time_unit.value}",
                "on_timeout":      ec.default_action_on_timeout.value,
                "rules": [
                    {"name": r.rule_name, "trigger": r.trigger.value, "action": r.action.value}
                    for r in ec.rules
                ],
            }

        return WorkflowPreviewResponse(
            workflow_id   = wf.id,
            workflow_name = wf.workflow_name,
            stages        = stages_preview,
            auto_rules    = auto_rules_preview,
            escalation    = escalation_preview,
            actions       = None,  
            integration   = None,
        )



class StageService:

    @staticmethod
    def create(db: Session, workflow_id: int,
               payload: WorkflowStageCreate) -> WorkflowStage:
        stage = WorkflowStage(
            workflow_id  = workflow_id,
            stage_order  = payload.stage_order,
            stage_name   = payload.stage_name,
            timeout      = payload.timeout,
            timeout_unit = payload.timeout_unit,
            status       = payload.status,
        )
        db.add(stage)
        db.flush()
        for apv in payload.approvers:
            db.add(WorkflowApprover(stage_id=stage.id, **apv.model_dump()))
        return stage

    @staticmethod
    def update(db: Session, stage_id: int,
               payload: WorkflowStageUpdate) -> WorkflowStage:
        stage = db.get(WorkflowStage, stage_id)
        if not stage:
            raise LookupError(f"Stage {stage_id} not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(stage, field, value)
        db.commit()
        db.refresh(stage)
        return stage

    @staticmethod
    def delete(db: Session, stage_id: int) -> None:
        stage = db.get(WorkflowStage, stage_id)
        if not stage:
            raise LookupError(f"Stage {stage_id} not found.")
        db.delete(stage)
        db.commit()



class ApproverService:

    @staticmethod
    def add(db: Session, stage_id: int,
            payload: WorkflowApproverCreate) -> WorkflowApprover:
        stage = db.get(WorkflowStage, stage_id)
        if not stage:
            raise LookupError(f"Stage {stage_id} not found.")
        apv = WorkflowApprover(stage_id=stage_id, **payload.model_dump())
        db.add(apv)
        db.commit()
        db.refresh(apv)
        return apv

    @staticmethod
    def update(db: Session, approver_id: int,
               payload: WorkflowApproverUpdate) -> WorkflowApprover:
        apv = db.get(WorkflowApprover, approver_id)
        if not apv:
            raise LookupError(f"Approver {approver_id} not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(apv, field, value)
        db.commit()
        db.refresh(apv)
        return apv

    @staticmethod
    def delete(db: Session, approver_id: int) -> None:
        apv = db.get(WorkflowApprover, approver_id)
        if not apv:
            raise LookupError(f"Approver {approver_id} not found.")
        db.delete(apv)
        db.commit()


class AutoApprovalRuleService:

    @staticmethod
    def create(db: Session, workflow_id: int,
               payload: AutoApprovalRuleCreate) -> AutoApprovalRule:
        rule = AutoApprovalRule(workflow_id=workflow_id, **payload.model_dump())
        db.add(rule)
        db.flush()
        return rule

    @staticmethod
    def update(db: Session, rule_id: int,
               payload: AutoApprovalRuleUpdate) -> AutoApprovalRule:
        rule = db.get(AutoApprovalRule, rule_id)
        if not rule:
            raise LookupError(f"Auto-approval rule {rule_id} not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete(db: Session, rule_id: int) -> None:
        rule = db.get(AutoApprovalRule, rule_id)
        if not rule:
            raise LookupError(f"Auto-approval rule {rule_id} not found.")
        db.delete(rule)
        db.commit()

    @staticmethod
    def evaluate(rules: List[AutoApprovalRule],
                 fields: Dict[str, Any]) -> Optional[str]:

        import operator as op
        OPS = {
            "lte": op.le, "gte": op.ge, "lt": op.lt,
            "gt": op.gt,  "eq": op.eq,  "neq": op.ne,
        }
        for rule in sorted(rules, key=lambda r: r.rule_order):
            if not rule.is_active:
                continue
            field_val = fields.get(rule.condition_field)
            if field_val is None:
                continue
            try:
                cmp_val = type(field_val)(rule.condition_value)
                op_fn = OPS.get(rule.operator.value)
                if op_fn and op_fn(field_val, cmp_val):
                    return rule.action.value
                # Handle IN / NOT_IN
                if rule.operator.value == "in":
                    allowed = [type(field_val)(v.strip()) for v in rule.condition_value.split(",")]
                    if field_val in allowed:
                        return rule.action.value
                if rule.operator.value == "not_in":
                    excluded = [type(field_val)(v.strip()) for v in rule.condition_value.split(",")]
                    if field_val not in excluded:
                        return rule.action.value
            except (TypeError, ValueError):
                continue
        return None


class EscalationService:

    @staticmethod
    def create_or_update_config(db: Session, workflow_id: int,
                                payload: EscalationConfigCreate) -> EscalationConfiguration:
        existing = db.execute(
            select(EscalationConfiguration)
            .where(EscalationConfiguration.workflow_id == workflow_id)
        ).scalars().first()

        data = payload.model_dump(exclude={"rules"})
        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            config = existing
        else:
            config = EscalationConfiguration(workflow_id=workflow_id, **data)
            db.add(config)
            db.flush()

 
        db.execute(

            EscalationRule.__table__.delete().where(
                EscalationRule.escalation_config_id == config.id
            )
        )
        for rule_data in payload.rules:
            db.add(EscalationRule(escalation_config_id=config.id, **rule_data.model_dump()))

        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def update_config(db: Session, workflow_id: int,
                      payload: EscalationConfigUpdate) -> EscalationConfiguration:
        config = db.execute(
            select(EscalationConfiguration)
            .where(EscalationConfiguration.workflow_id == workflow_id)
        ).scalars().first()
        if not config:
            raise LookupError(f"No escalation config for workflow {workflow_id}.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
        config.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def add_rule(db: Session, config_id: int,
                 payload: EscalationRuleCreate) -> EscalationRule:
        rule = EscalationRule(escalation_config_id=config_id, **payload.model_dump())
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def update_rule(db: Session, rule_id: int,
                    payload: EscalationRuleUpdate) -> EscalationRule:
        rule = db.get(EscalationRule, rule_id)
        if not rule:
            raise LookupError(f"Escalation rule {rule_id} not found.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(rule, field, value)
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete_rule(db: Session, rule_id: int) -> None:
        rule = db.get(EscalationRule, rule_id)
        if not rule:
            raise LookupError(f"Escalation rule {rule_id} not found.")
        db.delete(rule)
        db.commit()



class ActionsConfigService:

    @staticmethod
    def create_or_update(db: Session, workflow_id: int,
                         payload: WorkflowActionsConfigCreate) -> WorkflowActionsConfiguration:
        existing = db.execute(
            select(WorkflowActionsConfiguration)
            .where(WorkflowActionsConfiguration.workflow_id == workflow_id)
        ).scalars().first()

        data = payload.model_dump()
        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            cfg = WorkflowActionsConfiguration(workflow_id=workflow_id, **data)
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
            return cfg

    @staticmethod
    def update(db: Session, workflow_id: int,
               payload: WorkflowActionsConfigUpdate) -> WorkflowActionsConfiguration:
        cfg = db.execute(
            select(WorkflowActionsConfiguration)
            .where(WorkflowActionsConfiguration.workflow_id == workflow_id)
        ).scalars().first()
        if not cfg:
            raise LookupError(f"No actions config for workflow {workflow_id}.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(cfg, field, value)
        cfg.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(cfg)
        return cfg



class IntegrationConfigService:

    @staticmethod
    def create_or_update(db: Session, workflow_id: int,
                         payload: WorkflowIntegrationConfigCreate) -> WorkflowIntegrationConfiguration:
        existing = db.execute(
            select(WorkflowIntegrationConfiguration)
            .where(WorkflowIntegrationConfiguration.workflow_id == workflow_id)
        ).scalars().first()

        data = payload.model_dump()
        if existing:
            for field, value in data.items():
                setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            cfg = WorkflowIntegrationConfiguration(workflow_id=workflow_id, **data)
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
            return cfg

    @staticmethod
    def update(db: Session, workflow_id: int,
               payload: WorkflowIntegrationConfigUpdate) -> WorkflowIntegrationConfiguration:
        cfg = db.execute(
            select(WorkflowIntegrationConfiguration)
            .where(WorkflowIntegrationConfiguration.workflow_id == workflow_id)
        ).scalars().first()
        if not cfg:
            raise LookupError(f"No integration config for workflow {workflow_id}.")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(cfg, field, value)
        cfg.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(cfg)
        return cfg

    @staticmethod
    def run_integration_tests(db: Session,
                              workflow_id: int) -> IntegrationTestResponse:

        cfg = db.execute(
            select(WorkflowIntegrationConfiguration)
            .where(WorkflowIntegrationConfiguration.workflow_id == workflow_id)
        ).scalars().first()

        results: List[IntegrationTestResultItem] = []
        tested_at = datetime.utcnow()

        enabled = cfg.enabled_integrations if cfg else INTEGRATION_SYSTEM_CHOICES

        for key in enabled:
           
            success = True
            message = "Connection successful (stub)"
            results.append(IntegrationTestResultItem(
                integration_key=key,
                status="success" if success else "failure",
                message=message,
            ))
            db.add(IntegrationTestLog(
                workflow_id      = workflow_id,
                integration_key  = key,
                status           = "success" if success else "failure",
                response_payload = {"stub": True},
                tested_at        = tested_at,
            ))

        if cfg:
            cfg.last_test_run_at = tested_at
            cfg.last_test_result = [r.model_dump() for r in results]

        db.commit()
        return IntegrationTestResponse(
            workflow_id=workflow_id,
            tested_at=tested_at,
            results=results,
        )

    @staticmethod
    def get_integration_logs(db: Session,
                             workflow_id: int,
                             limit: int = 50) -> List[IntegrationTestLog]:
        return db.execute(
            select(IntegrationTestLog)
            .where(IntegrationTestLog.workflow_id == workflow_id)
            .order_by(IntegrationTestLog.tested_at.desc())
            .limit(limit)
        ).scalars().all()



class WorkflowEngineService:
   

    @staticmethod
    def initiate(db: Session,
                 payload: WorkflowEngineInstanceCreate) -> WorkflowEngineInstance:
        wf = _load_full_workflow(db, payload.workflow_id)
        if not wf:
            raise LookupError(f"Workflow {payload.workflow_id} not found.")
        if wf.status.value != "active":
            raise ValueError("Cannot initiate a non-active workflow.")


        auto_action = None
        if wf.auto_approval_rules and payload.metadata_json:
            auto_action = AutoApprovalRuleService.evaluate(
                wf.auto_approval_rules, payload.metadata_json
            )

        initial_status = InstanceStatusEnum.PENDING
        if auto_action == "auto_approve":
            initial_status = InstanceStatusEnum.APPROVED
        elif auto_action == "auto_reject":
            initial_status = InstanceStatusEnum.REJECTED

        instance = WorkflowEngineInstance(
            workflow_id         = payload.workflow_id,
            reference_type      = payload.reference_type,
            reference_id        = payload.reference_id,
            initiated_by        = payload.initiated_by,
            metadata_json       = payload.metadata_json,
            current_stage_order = 1,
            status              = initial_status,
            completed_at        = datetime.utcnow() if auto_action else None,
        )
        db.add(instance)
        db.flush()

        if auto_action:
            db.add(WorkflowStageLog(
                instance_id = instance.id,
                action      = auto_action,
                action_by   = "system",
                comments    = f"Auto-rule triggered: {auto_action}",
            ))

        db.commit()
        db.refresh(instance)
        return instance

    @staticmethod
    def apply_action(db: Session,
                     instance_id: int,
                     payload: StageActionPayload) -> WorkflowEngineInstance:
        instance = db.execute(
            select(WorkflowEngineInstance)
            .options(selectinload(WorkflowEngineInstance.stage_logs))
            .where(WorkflowEngineInstance.id == instance_id)
        ).scalars().first()
        if not instance:
            raise LookupError(f"Instance {instance_id} not found.")
        if instance.status in (InstanceStatusEnum.APPROVED,
                                InstanceStatusEnum.REJECTED,
                                InstanceStatusEnum.CANCELLED):
            raise ValueError(f"Cannot act on a {instance.status.value} instance.")

        wf = _load_full_workflow(db, instance.workflow_id)

       
        current_stage = next(
            (s for s in wf.stages if s.stage_order == instance.current_stage_order),
            None,
        )

        db.add(WorkflowStageLog(
            instance_id    = instance.id,
            stage_id       = current_stage.id if current_stage else None,
            stage_name     = current_stage.stage_name if current_stage else None,
            action         = payload.action,
            action_by      = payload.action_by,
            action_by_role = payload.action_by_role,
            comments       = payload.comments,
            ip_address     = payload.ip_address,
        ))

        action = payload.action.lower()

        if action == "approved":
 
            next_stage = next(
                (s for s in wf.stages
                 if s.stage_order == instance.current_stage_order + 1
                 and s.status.value == "enabled"),
                None,
            )
            if next_stage:
                instance.current_stage_order = next_stage.stage_order
                instance.status = InstanceStatusEnum.IN_PROGRESS
            else:
                instance.status    = InstanceStatusEnum.APPROVED
                instance.completed_at = datetime.utcnow()

        elif action == "rejected":
            instance.status       = InstanceStatusEnum.REJECTED
            instance.completed_at = datetime.utcnow()

        elif action == "escalated":
            instance.status = InstanceStatusEnum.ESCALATED

        elif action in ("sent_back", "info_requested", "delegated"):
            instance.status = InstanceStatusEnum.IN_PROGRESS

        instance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(instance)
        return instance

    @staticmethod
    def get_instance(db: Session, instance_id: int) -> Optional[WorkflowEngineInstance]:
        return db.execute(
            select(WorkflowEngineInstance)
            .options(selectinload(WorkflowEngineInstance.stage_logs))
            .where(WorkflowEngineInstance.id == instance_id)
        ).scalars().first()

    @staticmethod
    def list_instances(db: Session,
                       workflow_id: Optional[int]   = None,
                       status:      Optional[str]   = None,
                       reference_type: Optional[str] = None,
                       skip: int = 0,
                       limit: int = 50) -> List[WorkflowEngineInstance]:
        q = select(WorkflowEngineInstance)
        if workflow_id:
            q = q.where(WorkflowEngineInstance.workflow_id == workflow_id)
        if status:
            q = q.where(WorkflowEngineInstance.status == status)
        if reference_type:
            q = q.where(WorkflowEngineInstance.reference_type == reference_type)
        q = q.order_by(WorkflowEngineInstance.created_at.desc()).offset(skip).limit(limit)
        return db.execute(q).scalars().all()