
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date


class KPICardSchema(BaseModel):
    count:      int
    label:      str
    subLabel:   str
    severity:   str                  
    changeDir:  Optional[str] = None 
    unit:       Optional[str] = None 


class KPIResponseSchema(BaseModel):
    highRiskEmployees: KPICardSchema
    pendingAlerts:     KPICardSchema
    highPriorityItems: KPICardSchema
    modelAccuracy:     KPICardSchema


class ComparisonMetricSchema(BaseModel):
    value:     float
    change:    float
    changeDir: str     
    label:     str


class InsightComparisonSchema(BaseModel):
    attritionRate: ComparisonMetricSchema
    anomalies:     ComparisonMetricSchema
    avgRiskScore:  ComparisonMetricSchema


class RiskBucketSchema(BaseModel):
    count:      int
    percentage: float
    label:      str


class RiskDistributionSchema(BaseModel):
    high:   RiskBucketSchema
    medium: RiskBucketSchema
    low:    RiskBucketSchema
    total:  int


class AnomalyTrendSchema(BaseModel):
    period:    str    
    total:     int
    anomalies: int
    normal:    int


class RiskCorrelationSchema(BaseModel):
    employeeId:   int
    department:   str
    tenureMonths: float
    riskScore:    int
    riskLevel:    str  

class AttritionRiskSchema(BaseModel):
    employeeId: str
    name:       str
    department: str
    location:   str
    joinDate:   str
    tenure:     str
    riskScore:  int
    riskLevel:  str   
    reason:     str


class AlertSchema(BaseModel):
    id:       int
    action:   str
    count:    Optional[int] = None
    severity: str         
    color:    str         
    status:   Optional[str] = None
    badge:    Optional[str] = None
    endpoint: str


class AlertResponseSchema(BaseModel):
    alertCount: int
    alerts:     List[AlertSchema]


class ModelSchema(BaseModel):
    name:        str
    accuracy:    float
    status:      str   
    description: str


class ModelPerformanceSchema(BaseModel):
    activeModel:     str
    modelVersion:    str
    models:          List[ModelSchema]
    overallAccuracy: float


class RecentInsightSchema(BaseModel):
    module:   str  
    message:  str
    severity: str   
    color:    str    
    time:     str


class RecentInsightsResponseSchema(BaseModel):
    insights: List[RecentInsightSchema]


class AttendanceAnomalySchema(BaseModel):
    date:        str
    absentCount: int
    severity:    str  


class AttendanceAnomalyResponseSchema(BaseModel):
    month:            int
    year:             int
    anomalyThreshold: int
    anomalies:        List[AttendanceAnomalySchema]



class LeavePatternSchema(BaseModel):
    month:     str
    count:     int
    vsAverage: float
    isSpike:   bool


class PayrollAnomalySchema(BaseModel):
    employeeCode: str
    employeeName: str
    netPay:       float
    vsAverage:    float
    flag:         str   


class PayrollAnomalyResponseSchema(BaseModel):
    averageNetPay: float
    anomalyCount:  int
    anomalies:     List[PayrollAnomalySchema]


class WorkforceTrendSchema(BaseModel):
    month:               str
    newJoiners:          int
    cumulativeHeadcount: int
