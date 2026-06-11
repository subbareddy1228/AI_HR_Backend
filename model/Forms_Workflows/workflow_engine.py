
from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, JSON, String, Text,
)
from sqlalchemy.orm import relationship
from core.database import Base

import enum

class WorkflowTypeEnum(str, enum.Enum):
    LINEAR_SEQUENTIAL  = "linear_sequential"
    PARALLEL           = "parallel"
    MAJORITY_VOTE      = "majority_vote"
    ANY_APPROVER       = "any_approver"
    CUSTOM             = "custom"


class WorkflowStatusEnum(str, enum.Enum):
    ACTIVE   = "active"
    DISABLED = "disabled"
    DRAFT    = "draft"


class StageStatusEnum(str, enum.Enum):
    ENABLED  = "enabled"
    DISABLED = "disabled"


class AutoRuleActionEnum(str, enum.Enum):
    AUTO_APPROVE = "auto_approve"
    AUTO_REJECT  = "auto_reject"
    SKIP_STAGE   = "skip_stage"


class AutoRuleOperatorEnum(str, enum.Enum):
    LESS_THAN_OR_EQUAL    = "lte"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN             = "lt"
    GREATER_THAN          = "gt"
    EQUAL                 = "eq"
    NOT_EQUAL             = "neq"
    IN                    = "in"
    NOT_IN                = "not_in"


class EscalationActionEnum(str, enum.Enum):
    ESCALATE_NEXT_LEVEL   = "escalate_next_level"
    ESCALATE_SKIP_LEVEL   = "escalate_skip_level"
    AUTO_APPROVE          = "auto_approve"
    AUTO_REJECT           = "auto_reject"
    DELEGATE_BACKUP       = "delegate_backup"
    NOTIFY_ONLY           = "notify_only"


class EscalationTriggerEnum(str, enum.Enum):
    TIMEOUT    = "timeout"
    OUT_OF_OFFICE = "out_of_office"
    CUSTOM     = "custom"


class IntegrationModeEnum(str, enum.Enum):
    REAL_TIME = "real_time"
    BATCH     = "batch"
    WEBHOOK   = "webhook"


class ErrorHandlingEnum(str, enum.Enum):
    RETRY          = "retry"
    SKIP           = "skip"
    ALERT_ONLY     = "alert_only"
    ROLLBACK       = "rollback"


class TimeoutUnitEnum(str, enum.Enum):
    MINUTES = "minutes"
    HOURS   = "hours"
    DAYS    = "days"


class InstanceStatusEnum(str, enum.Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED    = "approved"
    REJECTED    = "rejected"
    CANCELLED   = "cancelled"
    ESCALATED   = "escalated"


class WorkflowConfiguration(Base):

    __tablename__ = "workflow_configurations"

    id = Column(Integer, primary_key=True, index=True)

    # Identity
    workflow_name        = Column(String(255), unique=True, nullable=False, index=True)
    description          = Column(Text, nullable=True)
    reference_type       = Column(String(100), nullable=True,
                                  comment="leave/expense/exit/transfer/promotion/custom")

    workflow_type        = Column(
        Enum(WorkflowTypeEnum), nullable=False,
        default=WorkflowTypeEnum.LINEAR_SEQUENTIAL
    )
    default_timeout      = Column(Integer, default=24,   comment="Numeric part of timeout")
    default_timeout_unit = Column(
        Enum(TimeoutUnitEnum), default=TimeoutUnitEnum.HOURS
    )


    status               = Column(Enum(WorkflowStatusEnum), default=WorkflowStatusEnum.ACTIVE)
    is_template          = Column(Boolean, default=False)
    created_by           = Column(String(100), nullable=True)
    updated_by           = Column(String(100), nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

 
    stages               = relationship("WorkflowStage",    back_populates="workflow",
                                        cascade="all, delete-orphan", order_by="WorkflowStage.stage_order")
    auto_approval_rules  = relationship("AutoApprovalRule", back_populates="workflow",
                                        cascade="all, delete-orphan")
    escalation_config    = relationship("EscalationConfiguration", back_populates="workflow",
                                        uselist=False, cascade="all, delete-orphan")
    actions_config       = relationship("WorkflowActionsConfiguration", back_populates="workflow",
                                        uselist=False, cascade="all, delete-orphan")
    integration_config   = relationship("WorkflowIntegrationConfiguration", back_populates="workflow",
                                        uselist=False, cascade="all, delete-orphan")
    instances            = relationship("WorkflowEngineInstance", back_populates="workflow")


class WorkflowStage(Base):
 
    __tablename__ = "workflow_stages"

    id              = Column(Integer, primary_key=True, index=True)
    workflow_id     = Column(Integer, ForeignKey("workflow_configurations.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    stage_order     = Column(Integer, nullable=False, default=1)
    stage_name      = Column(String(255), nullable=False)
    timeout         = Column(Integer, nullable=True,  comment="Override; falls back to workflow default")
    timeout_unit    = Column(Enum(TimeoutUnitEnum), default=TimeoutUnitEnum.HOURS)
    status          = Column(Enum(StageStatusEnum),  default=StageStatusEnum.ENABLED)
    created_at      = Column(DateTime, default=datetime.utcnow)

    workflow        = relationship("WorkflowConfiguration", back_populates="stages")
    approvers       = relationship("WorkflowApprover", back_populates="stage",
                                   cascade="all, delete-orphan")


class WorkflowApprover(Base):

    __tablename__ = "workflow_approvers"

    id              = Column(Integer, primary_key=True, index=True)
    stage_id        = Column(Integer, ForeignKey("workflow_stages.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    approver_type   = Column(String(50), default="user",
                             comment="user | role | dynamic (direct_manager, skip_manager, etc.)")
    approver_ref    = Column(String(255), nullable=False,
                             comment="user_id, role name, or dynamic keyword")
    display_name    = Column(String(255), nullable=True)
    is_backup       = Column(Boolean, default=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    stage           = relationship("WorkflowStage", back_populates="approvers")


class AutoApprovalRule(Base):
   
    __tablename__ = "auto_approval_rules"

    id              = Column(Integer, primary_key=True, index=True)
    workflow_id     = Column(Integer, ForeignKey("workflow_configurations.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    rule_order      = Column(Integer, default=1)
    condition_field = Column(String(100), nullable=False,
                             comment="amount | leave_type | department | frequency | custom_field_key")
    operator        = Column(Enum(AutoRuleOperatorEnum), nullable=False,
                             default=AutoRuleOperatorEnum.LESS_THAN_OR_EQUAL)
    condition_value = Column(String(500), nullable=False,
                             comment="Scalar or comma-separated list for IN/NOT_IN")
    action          = Column(Enum(AutoRuleActionEnum), nullable=False,
                             default=AutoRuleActionEnum.AUTO_APPROVE)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow        = relationship("WorkflowConfiguration", back_populates="auto_approval_rules")



class EscalationConfiguration(Base):
 
    __tablename__ = "escalation_configurations"

    id                               = Column(Integer, primary_key=True, index=True)
    workflow_id                      = Column(Integer, ForeignKey("workflow_configurations.id",
                                             ondelete="CASCADE"), nullable=False, unique=True, index=True)

    
    default_escalation_time          = Column(Integer, default=48)
    default_escalation_time_unit     = Column(Enum(TimeoutUnitEnum), default=TimeoutUnitEnum.HOURS)
    default_action_on_timeout        = Column(Enum(EscalationActionEnum),
                                              default=EscalationActionEnum.ESCALATE_NEXT_LEVEL)

  
    auto_assign_backup_approver      = Column(Boolean, default=True)
    send_email_to_primary_on_ooo     = Column(Boolean, default=True)
    create_calendar_reminder         = Column(Boolean, default=True)

  
    allow_approvers_to_delegate      = Column(Boolean, default=True)
    require_manager_approval_for_delegation = Column(Boolean, default=False)
    limit_delegation_duration        = Column(Boolean, default=True)
    max_delegation_duration_days     = Column(Integer, default=30)

    created_at                       = Column(DateTime, default=datetime.utcnow)
    updated_at                       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow                         = relationship("WorkflowConfiguration",
                                                    back_populates="escalation_config")
    rules                            = relationship("EscalationRule", back_populates="escalation_config",
                                                    cascade="all, delete-orphan")


class EscalationRule(Base):

    __tablename__ = "escalation_rules"

    id                      = Column(Integer, primary_key=True, index=True)
    escalation_config_id    = Column(Integer, ForeignKey("escalation_configurations.id",
                                     ondelete="CASCADE"), nullable=False, index=True)
    rule_name               = Column(String(255), nullable=False)
    trigger                 = Column(Enum(EscalationTriggerEnum), nullable=False)
    trigger_timeout         = Column(Integer, nullable=True,   comment="Used when trigger=timeout")
    trigger_timeout_unit    = Column(Enum(TimeoutUnitEnum), nullable=True)
    action                  = Column(Enum(EscalationActionEnum), nullable=False)
    notify_original_approver= Column(Boolean, default=True)
    is_active               = Column(Boolean, default=True)
    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    escalation_config       = relationship("EscalationConfiguration", back_populates="rules")


class WorkflowActionsConfiguration(Base):

    __tablename__ = "workflow_actions_configurations"

    id                          = Column(Integer, primary_key=True, index=True)
    workflow_id                 = Column(Integer, ForeignKey("workflow_configurations.id",
                                         ondelete="CASCADE"), nullable=False, unique=True, index=True)

   
    require_comments_on_approval    = Column(Boolean, default=True)
    require_reason_on_rejection     = Column(Boolean, default=True)
    allow_send_back_for_modification= Column(Boolean, default=True)
    request_additional_information  = Column(Boolean, default=True)
    conditional_approval_with_modifications = Column(Boolean, default=True)
    enable_bulk_approval            = Column(Boolean, default=True)

  
    email_notifications             = Column(Boolean, default=True)
    sms_notifications               = Column(Boolean, default=False)
    push_notifications              = Column(Boolean, default=True)
    slack_teams_notifications       = Column(Boolean, default=False)
    whatsapp_notifications          = Column(Boolean, default=False)

    log_all_approval_actions        = Column(Boolean, default=True)
    track_modification_history      = Column(Boolean, default=True)
    record_ip_addresses             = Column(Boolean, default=False)
    archive_completed_workflows     = Column(Boolean, default=True)
    approval_history_and_audit_trail= Column(Boolean, default=True)
    retention_period_days           = Column(Integer, default=365)

    created_at                      = Column(DateTime, default=datetime.utcnow)
    updated_at                      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow = relationship("WorkflowConfiguration", back_populates="actions_config")


INTEGRATION_SYSTEM_CHOICES = [
    "employee_master_data",
    "payroll_system",
    "document_generation",
    "calendar_events",
    "attendance_leave",
    "task_management",
    "audit_trail",
    "stakeholder_notifications",
    "crm_systems",
    "project_management",
]


class WorkflowIntegrationConfiguration(Base):

    __tablename__ = "workflow_integration_configurations"

    id                      = Column(Integer, primary_key=True, index=True)
    workflow_id             = Column(Integer, ForeignKey("workflow_configurations.id",
                                     ondelete="CASCADE"), nullable=False, unique=True, index=True)

    integration_mode        = Column(Enum(IntegrationModeEnum),
                                     default=IntegrationModeEnum.REAL_TIME)
    error_handling          = Column(Enum(ErrorHandlingEnum),
                                     default=ErrorHandlingEnum.RETRY)

   
    enabled_integrations    = Column(JSON, default=list,
                                     comment="e.g. ['employee_master_data','payroll_system']")

    
    integration_configs     = Column(JSON, nullable=True,
                                     comment="Dict keyed by integration key with override settings")

    last_test_run_at        = Column(DateTime, nullable=True)
    last_test_result        = Column(JSON, nullable=True,
                                     comment="Results from 'Test All Integrations'")

    created_at              = Column(DateTime, default=datetime.utcnow)
    updated_at              = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow = relationship("WorkflowConfiguration", back_populates="integration_config")


class WorkflowEngineInstance(Base):

    __tablename__ = "workflow_engine_instances"

    id                  = Column(Integer, primary_key=True, index=True)
    workflow_id         = Column(Integer, ForeignKey("workflow_configurations.id"), nullable=False, index=True)
    reference_type      = Column(String(100), nullable=True)
    reference_id        = Column(Integer, nullable=True)
    current_stage_order = Column(Integer, default=1)
    status              = Column(Enum(InstanceStatusEnum), default=InstanceStatusEnum.PENDING, index=True)
    initiated_by        = Column(String(100), nullable=True)
    completed_at        = Column(DateTime, nullable=True)
    metadata_json       = Column(JSON, nullable=True,
                                 comment="Snapshot of request fields for rule evaluation")
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workflow            = relationship("WorkflowConfiguration", back_populates="instances")
    stage_logs          = relationship("WorkflowStageLog", back_populates="instance",
                                       cascade="all, delete-orphan",
                                       order_by="WorkflowStageLog.created_at")


class WorkflowStageLog(Base):

    __tablename__ = "workflow_stage_logs"

    id              = Column(Integer, primary_key=True, index=True)
    instance_id     = Column(Integer, ForeignKey("workflow_engine_instances.id",
                             ondelete="CASCADE"), nullable=False, index=True)
    stage_id        = Column(Integer, ForeignKey("workflow_stages.id"), nullable=True)
    stage_name      = Column(String(255), nullable=True)
    action          = Column(String(50), nullable=False,
                             comment="approved|rejected|escalated|delegated|sent_back|info_requested")
    action_by       = Column(String(100), nullable=True)
    action_by_role  = Column(String(100), nullable=True)
    comments        = Column(Text, nullable=True)
    ip_address      = Column(String(45), nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    instance        = relationship("WorkflowEngineInstance", back_populates="stage_logs")

class IntegrationTestLog(Base):

    __tablename__ = "integration_test_logs"

    id                  = Column(Integer, primary_key=True, index=True)
    workflow_id         = Column(Integer, ForeignKey("workflow_configurations.id",
                                 ondelete="CASCADE"), nullable=False, index=True)
    integration_key     = Column(String(100), nullable=False)
    status              = Column(String(20), nullable=False,   comment="success|failure|skipped")
    response_payload    = Column(JSON, nullable=True)
    error_message       = Column(Text, nullable=True)
    tested_at           = Column(DateTime, default=datetime.utcnow)