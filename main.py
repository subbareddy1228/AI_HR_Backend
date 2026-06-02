# main.py
import os
import base64
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, select
from core.database import engine, Base
from model.models import User
from sqladmin import Admin, ModelView
 

# CREATE FASTAPI APP  (THIS MUST COME FIRST)

app = FastAPI(title="AI Recruitment HR Platform")






from routers.Reports import employee_reports, attendance_reports as rep_att, leave_reports, payroll_reports as rep_pay, compliance_reports, custom_report_builder, executive_dashboard, ai_insights



# CORS

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(employee_reports.router)