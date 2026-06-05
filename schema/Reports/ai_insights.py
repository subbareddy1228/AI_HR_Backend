# schema/Reports/ai_insights.py
# Response Schemas for AI-Driven Insights
# No model file needed — queries existing tables only

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date


# ── KPI Cards ─────────────────────────────────────────────────────────────────

class KPICardSchema(BaseModel):
    count:      int
    label:      str
    subLabel:   str
    severity:   str                  # high | warning | info | success
    changeDir:  Optional[str] = None # up | down | neutral
    unit:       Optional[str] = None # "%" for model accuracy


class KPIResponseSchema(BaseModel):
    highRiskEmployees: KPICardSchema
    pendingAlerts:     KPICardSchema
    highPriorityItems: KPICardSchema
    modelAccuracy:     KPICardSchema


# ── Insight Comparison ────────────────────────────────────────────────────────

class ComparisonMetricSchema(BaseModel):
    value:     float
    change:    float
    changeDir: str     # up | down | neutral
    label:     str


class InsightComparisonSchema(BaseModel):
    attritionRate: ComparisonMetricSchema
    anomalies:     ComparisonMetricSchema
    avgRiskScore:  ComparisonMetricSchema


# ── Risk Distribution ─────────────────────────────────────────────────────────

class RiskBucketSchema(BaseModel):
    count:      int
    percentage: float
    label:      str


class RiskDistributionSchema(BaseModel):
    high:   RiskBucketSchema
    medium: RiskBucketSchema
    low:    RiskBucketSchema
    total:  int


# ── Anomaly Trends ────────────────────────────────────────────────────────────

class AnomalyTrendSchema(BaseModel):
    period:    str    # Jan | Feb | ... or Week 1 | Day 1
    total:     int
    anomalies: int
    normal:    int


# ── Risk Factor Correlation ───────────────────────────────────────────────────

class RiskCorrelationSchema(BaseModel):
    employeeId:   int
    department:   str
    tenureMonths: float
    riskScore:    int
    riskLevel:    str   # High | Medium | Low


# ── Attrition Risk ────────────────────────────────────────────────────────────

class AttritionRiskSchema(BaseModel):
    employeeId: str
    name:       str
    department: str
    location:   str
    joinDate:   str
    tenure:     str
    riskScore:  int
    riskLevel:  str   # High | Medium | Low
    reason:     str


# ── Alerts ────────────────────────────────────────────────────────────────────

class AlertSchema(BaseModel):
    id:       int
    action:   str
    count:    Optional[int] = None
    severity: str           # high | warning | info | success
    color:    str           # danger | warning | primary | success
    status:   Optional[str] = None
    badge:    Optional[str] = None
    endpoint: str


class AlertResponseSchema(BaseModel):
    alertCount: int
    alerts:     List[AlertSchema]


# ── AI Model Performance ──────────────────────────────────────────────────────

class ModelSchema(BaseModel):
    name:        str
    accuracy:    float
    status:      str    # active | inactive
    description: str


class ModelPerformanceSchema(BaseModel):
    activeModel:     str
    modelVersion:    str
    models:          List[ModelSchema]
    overallAccuracy: float


# ── Recent Insights ───────────────────────────────────────────────────────────

class RecentInsightSchema(BaseModel):
    module:   str    # Attendance | Leave | Expense
    message:  str
    severity: str    # high | medium | low
    color:    str    # danger | warning | success
    time:     str


class RecentInsightsResponseSchema(BaseModel):
    insights: List[RecentInsightSchema]


# ── Attendance Anomalies ──────────────────────────────────────────────────────

class AttendanceAnomalySchema(BaseModel):
    date:        str
    absentCount: int
    severity:    str   # High | Medium


class AttendanceAnomalyResponseSchema(BaseModel):
    month:            int
    year:             int
    anomalyThreshold: int
    anomalies:        List[AttendanceAnomalySchema]


# ── Leave Patterns ────────────────────────────────────────────────────────────

class LeavePatternSchema(BaseModel):
    month:     str
    count:     int
    vsAverage: float
    isSpike:   bool


# ── Payroll Anomalies ─────────────────────────────────────────────────────────

class PayrollAnomalySchema(BaseModel):
    employeeCode: str
    employeeName: str
    netPay:       float
    vsAverage:    float
    flag:         str   # Zero/Very Low | Unusually High


class PayrollAnomalyResponseSchema(BaseModel):
    averageNetPay: float
    anomalyCount:  int
    anomalies:     List[PayrollAnomalySchema]


# ── Workforce Trend ───────────────────────────────────────────────────────────

class WorkforceTrendSchema(BaseModel):
    month:               str
    newJoiners:          int
    cumulativeHeadcount: int
