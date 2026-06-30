
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from model.Forms_Workflows.workflow_engine import (
    AutoRuleActionEnum,
    AutoRuleOperatorEnum,
    ErrorHandlingEnum,
    EscalationActionEnum,
    EscalationTriggerEnum,
    InstanceStatusEnum,
    IntegrationModeEnum,
    StageStatusEnum,
    TimeoutUnitEnum,
    WorkflowStatusEnum,
    WorkflowTypeEnum,
    INTEGRATION_SYSTEM_CHOICES,
)


class WorkflowApproverBase(BaseModel):
    approver_type: str = Field("user", description="user | role | dynamic")
    approver_ref:  str = Field(..., description="user_id, role name, or dynamic keyword")
    display_name:  Optional[str] = None
    is_backup:     bool = False


class WorkflowApproverCreate(WorkflowApproverBase):
    pass


class WorkflowApproverUpdate(BaseModel):
    approver_type: Optional[str] = None
    approver_ref:  Optional[str] = None
    display_name:  Optional[str] = None
    is_backup:     Optional[bool] = None


class WorkflowApproverResponse(WorkflowApproverBase):
    id:         int
    stage_id:   int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowStageBase(BaseModel):
    stage_order:   int = Field(1, ge=1)
    stage_name:    str = Field(..., max_length=255)
    timeout:       Optional[int]    = Field(None, ge=1)
    timeout_unit:  TimeoutUnitEnum  = TimeoutUnitEnum.HOURS
    status:        StageStatusEnum  = StageStatusEnum.ENABLED


class WorkflowStageCreate(WorkflowStageBase):
    approvers: List[WorkflowApproverCreate] = []


class WorkflowStageUpdate(BaseModel):
    stage_order:   Optional[int]           = Field(None, ge=1)
    stage_name:    Optional[str]           = None
    timeout:       Optional[int]           = None
    timeout_unit:  Optional[TimeoutUnitEnum] = None
    status:        Optional[StageStatusEnum] = None


class WorkflowStageResponse(WorkflowStageBase):
    id:          int
    workflow_id: int
    approvers:   List[WorkflowApproverResponse] = []
    created_at:  datetime
    model_config = ConfigDict(from_attributes=True)


class AutoApprovalRuleBase(BaseModel):
    rule_order:       int                  = Field(1, ge=1)
    condition_field:  str                  = Field(..., max_length=100,
                                                   description="amount | leave_type | department | frequency | custom_field_key")
    operator:         AutoRuleOperatorEnum = AutoRuleOperatorEnum.LESS_THAN_OR_EQUAL
    condition_value:  str                  = Field(..., max_length=500)
    action:           AutoRuleActionEnum   = AutoRuleActionEnum.AUTO_APPROVE
    is_active:        bool                 = True


class AutoApprovalRuleCreate(AutoApprovalRuleBase):
    pass


class AutoApprovalRuleUpdate(BaseModel):
    rule_order:       Optional[int]                  = None
    condition_field:  Optional[str]                  = None
    operator:         Optional[AutoRuleOperatorEnum] = None
    condition_value:  Optional[str]                  = None
    action:           Optional[AutoRuleActionEnum]   = None
    is_active:        Optional[bool]                 = None


class AutoApprovalRuleResponse(AutoApprovalRuleBase):
    id:          int
    workflow_id: int
    created_at:  datetime
    updated_at:  datetime
    model_config = ConfigDict(from_attributes=True)


class EscalationRuleBase(BaseModel):
    rule_name:               str                    = Field(..., max_length=255)
    trigger:                 EscalationTriggerEnum
    trigger_timeout:         Optional[int]          = None
    trigger_timeout_unit:    Optional[TimeoutUnitEnum] = None
    action:                  EscalationActionEnum
    notify_original_approver: bool                  = True
    is_active:               bool                   = True


class EscalationRuleCreate(EscalationRuleBase):
    pass


class EscalationRuleUpdate(BaseModel):
    rule_name:               Optional[str]                    = None
    trigger:                 Optional[EscalationTriggerEnum]  = None
    trigger_timeout:         Optional[int]                    = None
    trigger_timeout_unit:    Optional[TimeoutUnitEnum]        = None
    action:                  Optional[EscalationActionEnum]   = None
    notify_original_approver: Optional[bool]                  = None
    is_active:               Optional[bool]                   = None


class EscalationRuleResponse(EscalationRuleBase):
    id:                    int
    escalation_config_id:  int
    created_at:            datetime
    updated_at:            datetime
    model_config = ConfigDict(from_attributes=True)


class EscalationConfigBase(BaseModel):
    default_escalation_time:              int                   = Field(48, ge=1)
    default_escalation_time_unit:         TimeoutUnitEnum       = TimeoutUnitEnum.HOURS
    default_action_on_timeout:            EscalationActionEnum  = EscalationActionEnum.ESCALATE_NEXT_LEVEL
    auto_assign_backup_approver:          bool = True
    send_email_to_primary_on_ooo:         bool = True
    create_calendar_reminder:             bool = True
    allow_approvers_to_delegate:          bool = True
    require_manager_approval_for_delegation: bool = False
    limit_delegation_duration:            bool = True
    max_delegation_duration_days:         int  = Field(30, ge=1)


class EscalationConfigCreate(EscalationConfigBase):
    rules: List[EscalationRuleCreate] = []


class EscalationConfigUpdate(BaseModel):
    default_escalation_time:              Optional[int]                   = None
    default_escalation_time_unit:         Optional[TimeoutUnitEnum]       = None
    default_action_on_timeout:            Optional[EscalationActionEnum]  = None
    auto_assign_backup_approver:          Optional[bool]                  = None
    send_email_to_primary_on_ooo:         Optional[bool]                  = None
    create_calendar_reminder:             Optional[bool]                  = None
    allow_approvers_to_delegate:          Optional[bool]                  = None
    require_manager_approval_for_delegation: Optional[bool]               = None
    limit_delegation_duration:            Optional[bool]                  = None
    max_delegation_duration_days:         Optional[int]                   = None


class EscalationConfigResponse(EscalationConfigBase):
    id:          int
    workflow_id: int
    rules:       List[EscalationRuleResponse] = []
    created_at:  datetime
    updated_at:  datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowActionsConfigBase(BaseModel):
    # Approval Actions
    require_comments_on_approval:             bool = True
    require_reason_on_rejection:              bool = True
    allow_send_back_for_modification:         bool = True
    request_additional_information:           bool = True
    conditional_approval_with_modifications:  bool = True
    enable_bulk_approval:                     bool = True
    # Notifications
    email_notifications:                      bool = True
    sms_notifications:                        bool = False
    push_notifications:                       bool = True
    slack_teams_notifications:                bool = False
    whatsapp_notifications:                   bool = False
    # Audit & History
    log_all_approval_actions:                 bool = True
    track_modification_history:               bool = True
    record_ip_addresses:                      bool = False
    archive_completed_workflows:              bool = True
    approval_history_and_audit_trail:         bool = True
    retention_period_days:                    int  = Field(365, ge=1)


class WorkflowActionsConfigCreate(WorkflowActionsConfigBase):
    pass


class WorkflowActionsConfigUpdate(BaseModel):
    require_comments_on_approval:             Optional[bool] = None
    require_reason_on_rejection:              Optional[bool] = None
    allow_send_back_for_modification:         Optional[bool] = None
    request_additional_information:           Optional[bool] = None
    conditional_approval_with_modifications:  Optional[bool] = None
    enable_bulk_approval:                     Optional[bool] = None
    email_notifications:                      Optional[bool] = None
    sms_notifications:                        Optional[bool] = None
    push_notifications:                       Optional[bool] = None
    slack_teams_notifications:                Optional[bool] = None
    whatsapp_notifications:                   Optional[bool] = None
    log_all_approval_actions:                 Optional[bool] = None
    track_modification_history:               Optional[bool] = None
    record_ip_addresses:                      Optional[bool] = None
    archive_completed_workflows:              Optional[bool] = None
    approval_history_and_audit_trail:         Optional[bool] = None
    retention_period_days:                    Optional[int]  = None


class WorkflowActionsConfigResponse(WorkflowActionsConfigBase):
    id:          int
    workflow_id: int
    created_at:  datetime
    updated_at:  datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowIntegrationConfigBase(BaseModel):
    integration_mode:       IntegrationModeEnum   = IntegrationModeEnum.REAL_TIME
    error_handling:         ErrorHandlingEnum      = ErrorHandlingEnum.RETRY
    enabled_integrations:   List[str]              = Field(default_factory=list)
    integration_configs:    Optional[Dict[str, Any]] = None

    @field_validator("enabled_integrations")
    @classmethod
    def validate_integration_keys(cls, v: List[str]) -> List[str]:
        invalid = [k for k in v if k not in INTEGRATION_SYSTEM_CHOICES]
        if invalid:
            raise ValueError(f"Unknown integration keys: {invalid}. "
                             f"Allowed: {INTEGRATION_SYSTEM_CHOICES}")
        return v


class WorkflowIntegrationConfigCreate(WorkflowIntegrationConfigBase):
    pass


class WorkflowIntegrationConfigUpdate(BaseModel):
    integration_mode:       Optional[IntegrationModeEnum]   = None
    error_handling:         Optional[ErrorHandlingEnum]      = None
    enabled_integrations:   Optional[List[str]]              = None
    integration_configs:    Optional[Dict[str, Any]]         = None


class IntegrationTestResultItem(BaseModel):
    integration_key: str
    status:          str 
    message:         Optional[str] = None
    response:        Optional[Any] = None


class IntegrationTestResponse(BaseModel):
    workflow_id: int
    tested_at:   datetime
    results:     List[IntegrationTestResultItem]


class WorkflowIntegrationConfigResponse(WorkflowIntegrationConfigBase):
    id:               int
    workflow_id:      int
    last_test_run_at: Optional[datetime] = None
    last_test_result: Optional[Any]      = None
    created_at:       datetime
    updated_at:       datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowConfigBase(BaseModel):
    workflow_name:        str                  = Field(..., max_length=255)
    description:          Optional[str]        = None
    reference_type:       Optional[str]        = None
    workflow_type:        WorkflowTypeEnum     = WorkflowTypeEnum.LINEAR_SEQUENTIAL
    default_timeout:      int                  = Field(24, ge=1)
    default_timeout_unit: TimeoutUnitEnum      = TimeoutUnitEnum.HOURS
    status:               WorkflowStatusEnum   = WorkflowStatusEnum.ACTIVE
    is_template:          bool                 = False


class WorkflowConfigCreate(WorkflowConfigBase):

    stages:             List[WorkflowStageCreate]               = []
    auto_approval_rules: List[AutoApprovalRuleCreate]           = []
    escalation_config:   Optional[EscalationConfigCreate]       = None
    actions_config:      Optional[WorkflowActionsConfigCreate]  = None
    integration_config:  Optional[WorkflowIntegrationConfigCreate] = None


class WorkflowConfigUpdate(BaseModel):
    workflow_name:        Optional[str]               = None
    description:          Optional[str]               = None
    reference_type:       Optional[str]               = None
    workflow_type:        Optional[WorkflowTypeEnum]  = None
    default_timeout:      Optional[int]               = None
    default_timeout_unit: Optional[TimeoutUnitEnum]   = None
    status:               Optional[WorkflowStatusEnum] = None
    is_template:          Optional[bool]              = None


class WorkflowConfigResponse(WorkflowConfigBase):
    id:                  int
    stages:              List[WorkflowStageResponse]                = []
    auto_approval_rules: List[AutoApprovalRuleResponse]             = []
    escalation_config:   Optional[EscalationConfigResponse]         = None
    actions_config:      Optional[WorkflowActionsConfigResponse]    = None
    integration_config:  Optional[WorkflowIntegrationConfigResponse] = None
    created_by:          Optional[str]                              = None
    updated_by:          Optional[str]                              = None
    created_at:          datetime
    updated_at:          datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowConfigSummary(BaseModel):
    id:             int
    workflow_name:  str
    workflow_type:  WorkflowTypeEnum
    status:         WorkflowStatusEnum
    stage_count:    int = 0
    created_at:     datetime
    model_config = ConfigDict(from_attributes=True)



class WorkflowStageLogResponse(BaseModel):
    id:             int
    instance_id:    int
    stage_id:       Optional[int]   = None
    stage_name:     Optional[str]   = None
    action:         str
    action_by:      Optional[str]   = None
    action_by_role: Optional[str]   = None
    comments:       Optional[str]   = None
    ip_address:     Optional[str]   = None
    created_at:     datetime
    model_config = ConfigDict(from_attributes=True)


class WorkflowEngineInstanceCreate(BaseModel):
    workflow_id:     int
    reference_type:  Optional[str]      = None
    reference_id:    Optional[int]      = None
    initiated_by:    Optional[str]      = None
    metadata_json:   Optional[Dict[str, Any]] = None


class WorkflowEngineInstanceResponse(BaseModel):
    id:                  int
    workflow_id:         int
    reference_type:      Optional[str] = None
    reference_id:        Optional[int] = None
    current_stage_order: int
    status:              InstanceStatusEnum
    initiated_by:        Optional[str] = None
    completed_at:        Optional[datetime] = None
    stage_logs:          List[WorkflowStageLogResponse] = []
    created_at:          datetime
    updated_at:          datetime
    model_config = ConfigDict(from_attributes=True)


class StageActionPayload(BaseModel):
    
    action:         str = Field(..., description="approved|rejected|sent_back|delegated|info_requested")
    action_by:      str
    action_by_role: Optional[str] = None
    comments:       Optional[str] = None
    ip_address:     Optional[str] = None


class WorkflowValidationResult(BaseModel):
    is_valid:  bool
    errors:    List[str] = []
    warnings:  List[str] = []


class WorkflowPreviewResponse(BaseModel):
    workflow_id:   int
    workflow_name: str
    stages:        List[Dict[str, Any]]
    auto_rules:    List[Dict[str, Any]]
    escalation:    Optional[Dict[str, Any]] = None
    actions:       Optional[Dict[str, Any]] = None
    integration:   Optional[Dict[str, Any]] = None