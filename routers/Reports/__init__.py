# routers/Reports/__init__.py
# Expose all report routers for easy import in main.py

from routers.Reports.employee_reports import router as employee_router
from routers.Reports.attendance_reports import router as attendance_router
from routers.Reports.leave_reports import router as leave_router
from routers.Reports.payroll_reports import router as payroll_router
from routers.Reports.compliance_reports import router as compliance_router
from routers.Reports.custom_report_builder import router as custom_router
from routers.Reports.executive_dashboard import router as dashboard_router
from routers.Reports.ai_insights import router as ai_insights_router

# ── Snippet to add to main.py (do NOT auto-apply) ──────────────────────────────
#
# from routers.Reports import (
#     employee_router, attendance_router, leave_router, payroll_router,
#     compliance_router, custom_router, dashboard_router, ai_insights_router,
# )
#
# app.include_router(employee_router,   prefix="/api/reports")
# app.include_router(attendance_router, prefix="/api/reports")
# app.include_router(leave_router,      prefix="/api/reports")
# app.include_router(payroll_router,    prefix="/api/reports")
# app.include_router(compliance_router, prefix="/api/reports")
# app.include_router(custom_router,     prefix="/api/reports")
# app.include_router(dashboard_router,  prefix="/api/reports")
# app.include_router(ai_insights_router,prefix="/api/reports")
