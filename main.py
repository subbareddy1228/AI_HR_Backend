
# # # main.py
# # import os
# # import base64
# # from fastapi import FastAPI, Request
# # from fastapi.responses import Response
# # from fastapi.middleware.cors import CORSMiddleware
# # from fastapi.staticfiles import StaticFiles
# # from sqlmodel import SQLModel, Session, select
# # from core.database import engine, Base
# # from model.models import User
# # from sqladmin import Admin, ModelView
 

# # # CREATE FASTAPI APP  (THIS MUST COME FIRST)

# # app = FastAPI(title="AI Recruitment HR Platform")
 
# # # ADMIN BASIC AUTH MIDDLEWARE

# # # @app.middleware("http")
# # # async def admin_protect(request: Request, call_next):
 
# # #     if request.url.path.startswith("/admin"):
# # #         auth = request.headers.get("Authorization")
 
# # #         if not auth or not auth.startswith("Basic "):
# # #             return Response(
# # #                 status_code=401,
# # #                 headers={
# # #                     "WWW-Authenticate": 'Basic realm="AdminPanel"',
# # #                     "Cache-Control": "no-store"
# # #                 },
# # #                 content="Authentication required"
# # #             )
 
# # #         try:
# # #             encoded = auth.split(" ")[1]
# # #             decoded = base64.b64decode(encoded).decode()
# # #             username, password = decoded.split(":", 1)
 
# # #             ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
# # #             ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
 
# # #             if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
# # #                 return Response(
# # #                     status_code=401,
# # #                     headers={
# # #                         "WWW-Authenticate": 'Basic realm="AdminPanel"',
# # #                         "Cache-Control": "no-store"
# # #                     },
# # #                     content="Invalid username or password"
# # #                 )
 
# # #         except Exception:
# # #             return Response(
# # #                 status_code=401,
# # #                 headers={
# # #                     "WWW-Authenticate": 'Basic realm="AdminPanel"',
# # #                     "Cache-Control": "no-store"
# # #                 },
# # #                 content="Invalid authentication format"
# # #             )
 
# # #     return await call_next(request)
 
 

# # # IMPORT ROUTERS

# # from routers.admin_users.auth import router as auth_router
# # from routers.jobs import router as jobs_router
# # from routers.admin_users.admin import router as admin_router, compat_router as admin_compat_router
# # from routers.candidates import router as candidates_router
# # from routers.admin_users.recruiter_dashboard import router as recruiter_dashboard_router
# # from routers.pipeline import router as pipeline_router
# # from routers.Analytics_Dashboard.analytics import router as analytics_router
# # from routers.HR_Automation.digital_signature.routers.documents import router as documents_router
# # from routers.HR_Automation.digital_signature.routers.signatures import router as signatures_router
# # from routers.Candidate_assessments.Assessment.Assessments.assessments_router import router as assessments_router
# # from routers.Candidate_assessments.Assessment.Assessments.assignments_router import router as assignments_router
# # from routers.Candidate_assessments.Assessment.Assessments.ai_interview_router import router as ai_interview_router
# # from routers.Candidate_assessments.Assessment.communication.comm_routes import router as comm_router
# # from routers.Candidate_assessments.Assessment.coding.coding import router as coding_router
# # from routers.Candidate_assessments.Assessment.Assessments.Assessment_Result.candidates import router as candidates_result_router
# # from routers.Candidate_assessments.Assessment.aptitude.routers import exam, results as aptitude_results
# # from routers.Basic_analytics.hiring_funnel.routers.hiring_funnel import router as hiring_funnel_router
# # from routers.Basic_analytics.hiring_funnel.routers.hiring_funnel import router as time_hire_router
# # from routers.HR_Automation.Task_Management.router.tasks_router import router as tasks_router
# # from routers.Resume_parsing.routers.resume_router import router as resume_router
# # from routers.admin_users.send_assessment_email import router as email_router
# # from routers.offers.offer_template_router import router as offer_template_router
# # from routers.offers.offer_tracking_router import router as offer_tracking_router
# # from routers.HR_Automation.Onboarding.routers import candidates as onboard_candidates, uploads
# # from routers.HR_Automation.attendance import daily, punches, shift
# # from routers.AI_Interview_Bot.routes import interviews
# # from routers.CRM import contacts, company, deals, leads, pipelines, activities, analytics,projects, clients, tasks
# # from routers.onboarding.admin_candidates import router as admin_candidates_router
# # from routers.onboarding import bank_details, present_address, statutory, onboarding, approval, employee, family_details, documents, personal_info, address
# # from routers.HR_Operations.Asset_Management import assets, asset_allocation, asset_return, asset_maintenance,asset_insurance
# # from routers.Company_Settings import currency, financial_year, localization, policy,company_profile
# # from routers.Payroll.salary_slip import router as salary_slip_router
# # from routers.Forms_Workflows.approvals import router as approvals_router

# # from routers.Employee_Management.org_hierarchy import router as org_hierarchy_router
# # # from routers.Employee_Management.employee_lifecycle import router as employee_lifecycle_router
 



# # # CORS

# # app.add_middleware(
# #     CORSMiddleware,
# #     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
# #     allow_credentials=True,
# #     allow_methods=["*"],
# #     allow_headers=["*"],
# # )
 


# # # STARTUP — CREATE TABLES & DEFAULT SUPERADMIN

# # # @app.on_event("startup")
# # # def on_startup():
# # #     try:
# # #         # Try to create tables
# # #         SQLModel.metadata.create_all(bind=engine)
# # #         Base.metadata.create_all(bind=engine)
# # #         print("✓ Database tables initialized successfully")
# # #     except Exception as e:
# # #         print(f"⚠ Warning: Could not create database tables: {e}")
# # #         print("  The application will continue, but database operations may fail.")
# # #         print("  Please ensure PostgreSQL is running and DATABASE_URL is correct.")
# # #         return  # Exit early if database connection fails
 
# # #     try:
# # #         # Try to create default superadmin
# # #         with Session(engine) as session:
# # #             superadmin = session.exec(select(User).where(User.role == "superadmin")).first()

# # #             if not superadmin:
# # #                 from passlib.context import CryptContext
# # #                 pwd = CryptContext(schemes=["bcrypt"])

# # #                 user = User(
# # #                     name="Super Admin",
# # #                     username="superadmin",
# # #                     email="superadmin@example.com",
# # #                     hashed_password=pwd.hash("admin123"),
# # #                     role="superadmin",
# # #                     is_active=True,
# # #                 )
# # #                 session.add(user)
# # #                 session.commit()
# # #                 print("✓ Default Super Admin created: superadmin / admin123")
# # #             else:
# # #                 print("✓ Super Admin already exists")
# # #     except Exception as e:
# # #         print(f"⚠ Warning: Could not create default superadmin: {e}")
# # #         print("  You may need to create it manually once the database is available.")
# # @app.on_event("startup")
# # def on_startup():
# #     print(">>> STARTUP BEGIN")
# #     try:
# #         print(">>> Creating SQLModel tables...")
# #         SQLModel.metadata.create_all(bind=engine)
# #         print(">>> SQLModel done")
# #         print(">>> Creating Base tables...")
# #         Base.metadata.create_all(bind=engine)
# #         print(">>> Base done")
# #         print("✓ Database tables initialized successfully")
# #     except Exception as e:
# #         print(f"⚠ Warning: Could not create database tables: {e}")
# #         return

# #     try:
# #         print(">>> Checking superadmin...")
# #         with Session(engine) as session:
# #             superadmin = session.exec(select(User).where(User.role == "superadmin")).first()
# #             if not superadmin:
# #                 from passlib.context import CryptContext
# #                 pwd = CryptContext(schemes=["bcrypt"])
# #                 user = User(
# #                     name="Super Admin",
# #                     username="superadmin",
# #                     email="superadmin@example.com",
# #                     hashed_password=pwd.hash("admin123"),
# #                     role="superadmin",
# #                     is_active=True,
# #                 )
# #                 session.add(user)
# #                 session.commit()
# #                 print("✓ Default Super Admin created")
# #             else:
# #                 print("✓ Super Admin already exists")
# #     except Exception as e:
# #         print(f"⚠ Warning: Could not create default superadmin: {e}")

# #     print(">>> STARTUP COMPLETE")
 

# # # SQLADMIN PANEL 
# # class UserAdmin(ModelView, model=User):
# #     column_list = [User.id, User.username, User.email, User.role, User.is_active, User.created_at]
# #     form_columns = [User.username, User.email, User.role, User.is_active]
# #     name = "User"
# #     name_plural = "Users"
# #     icon = "fa-solid fa-user"
 
# # admin = Admin(app=app, engine=engine, title="Super Admin Dashboard")
# # admin.add_view(UserAdmin)

# # # ROUTE REGISTRATION
# # app.include_router(auth_router)
# # app.include_router(jobs_router)
# # app.include_router(admin_router, prefix="/api/admin")
# # app.include_router(admin_compat_router)
# # app.include_router(candidates_router)
# # app.include_router(pipeline_router)
# # app.include_router(salary_slip_router)
# # app.include_router(recruiter_dashboard_router, prefix="/api/recruiter_dashboard")
# # app.include_router(analytics_router)
# # app.include_router(assessments_router)
# # app.include_router(assignments_router)
# # app.include_router(candidates_result_router, prefix="/api/assessment_results")
# # app.include_router(ai_interview_router)
# # app.include_router(comm_router, prefix="/comm")
# # app.include_router(coding_router, prefix="/coding")
# # app.include_router(exam.router, prefix="/api/assessment/aptitude")
# # app.include_router(aptitude_results.router, prefix="/api/assessment/aptitude")
# # app.include_router(hiring_funnel_router, prefix="/api/hiring_funnel")
# # app.include_router(time_hire_router, prefix="/api/time_to_hire")
# # app.include_router(daily.router, prefix="/attendance",tags=["Attendance Daily"])
# # app.include_router(punches.router, prefix="/attendance/punches", tags=["Attendance Punches"])
# # app.include_router(shift.router, prefix="/attendance/shifts", tags=["Shift Management"])
# # app.include_router(documents_router, prefix="/api/documents")
# # app.include_router(signatures_router, prefix="/api/signatures")
# # app.include_router(onboard_candidates.router, prefix="/api/candidates")
# # app.include_router(uploads.router, prefix="/api/uploads")
# # app.include_router(tasks_router, prefix="/api/tasks")
# # app.include_router(resume_router, prefix="/api/resume")
# # app.include_router(interviews.router, prefix="/api/interviews")
# # app.include_router(email_router)
# # app.include_router(offer_template_router, prefix="/api/offers")
# # app.include_router(offer_tracking_router, prefix="/api/offers")

# # # Additional CRM Modules
# # app.include_router(contacts.router,prefix="/contacts",tags=["contacts"])
# # app.include_router(company.router,prefix="/companies",tags=["companies"])
# # app.include_router(deals.router,prefix="/deals",tags=["deals"])
# # app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
# # # Legacy compatibility for existing frontend calls.
# # app.include_router(leads.router, prefix="/leads", tags=["leads-legacy"], include_in_schema=False)
# # app.include_router(pipelines.router,prefix="/pipelines",tags=["pipelines"])
# # app.include_router(activities.router,prefix="/activities",tags=["activities"])
# # app.include_router(analytics.router,prefix="/analytics",tags=["analytics"])
# # app.include_router(clients.router)
# # app.include_router(projects.router)
# # app.include_router(tasks.router)

# # # Onboarding Routes
    
# # app.include_router(admin_candidates_router)
# # app.include_router(bank_details.router)
# # app.include_router(present_address.router)
# # app.include_router(statutory.router)
# # app.include_router(onboarding.router)
# # app.include_router(approval.router)
# # app.include_router(employee.router)
# # app.include_router(family_details.router)
# # app.include_router(documents.router)
# # app.include_router(personal_info.router)
# # app.include_router(address.router)

# # # Company Settings - Currency Management
# # app.include_router(currency.router) 
# # app.include_router(financial_year.router)
# # app.include_router(localization.router)
# # app.include_router(policy.router)
# # app.include_router(company_profile.router)

# # #HR Operations - Assets Management
# # app.include_router(assets.router)
# # app.include_router(asset_allocation.router)
# # app.include_router(asset_return.router)
# # app.include_router(asset_maintenance.router)
# # app.include_router(asset_insurance.router)

# # #forms_workflows 
# # app.include_router(approvals_router)

# # #org hierarchy
# # app.include_router(org_hierarchy_router)
# # # app.include_router(employee_lifecycle_router)

# # # STATIC FILES

# # if not os.path.exists("uploads"):
# #     os.makedirs("uploads")
 
# # app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
 
# # # TEST ENDPOINT
# # @app.get("/api/test")
# # def test_api():
# #     return {"message": "Backend is working correctly!"}
# # main.py
# import os
# import base64
# from fastapi import FastAPI, Request
# from fastapi.responses import Response
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.staticfiles import StaticFiles
# from sqlmodel import SQLModel, Session, select
# from core.database import engine, Base
# from model.models import User
# from sqladmin import Admin, ModelView


# # CREATE FASTAPI APP (THIS MUST COME FIRST)
# app = FastAPI(title="AI Recruitment HR Platform")


# # IMPORT ROUTERS
# from routers.admin_users.auth import router as auth_router
# from routers.jobs import router as jobs_router
# from routers.admin_users.admin import router as admin_router, compat_router as admin_compat_router
# from routers.candidates import router as candidates_router
# from routers.admin_users.recruiter_dashboard import router as recruiter_dashboard_router
# from routers.pipeline import router as pipeline_router
# from routers.Analytics_Dashboard.analytics import router as analytics_router
# from routers.HR_Automation.digital_signature.routers.documents import router as documents_router
# from routers.HR_Automation.digital_signature.routers.signatures import router as signatures_router
# from routers.Candidate_assessments.Assessment.Assessments.assessments_router import router as assessments_router
# from routers.Candidate_assessments.Assessment.Assessments.assignments_router import router as assignments_router
# from routers.Candidate_assessments.Assessment.Assessments.ai_interview_router import router as ai_interview_router
# from routers.Candidate_assessments.Assessment.communication.comm_routes import router as comm_router
# from routers.Candidate_assessments.Assessment.coding.coding import router as coding_router
# from routers.Candidate_assessments.Assessment.Assessments.Assessment_Result.candidates import router as candidates_result_router
# from routers.Candidate_assessments.Assessment.aptitude.routers import exam, results as aptitude_results
# from routers.Basic_analytics.hiring_funnel.routers.hiring_funnel import router as hiring_funnel_router
# from routers.Basic_analytics.hiring_funnel.routers.hiring_funnel import router as time_hire_router
# from routers.HR_Automation.Task_Management.router.tasks_router import router as tasks_router
# from routers.Resume_parsing.routers.resume_router import router as resume_router
# from routers.admin_users.send_assessment_email import router as email_router
# from routers.offers.offer_template_router import router as offer_template_router
# from routers.offers.offer_tracking_router import router as offer_tracking_router
# from routers.HR_Automation.Onboarding.routers import candidates as onboard_candidates, uploads
# from routers.HR_Automation.attendance import attendance_capture, daily_punches, daily_attendance, monthly_attendance, shift
# from routers.AI_Interview_Bot.routes import interviews
# from routers.CRM import contacts, company, deals, leads, pipelines, activities, analytics, projects, clients, tasks
# from routers.onboarding.admin_candidates import router as admin_candidates_router
# from routers.onboarding import bank_details, present_address, statutory, onboarding, approval, employee, family_details, documents, personal_info, address
# from routers.HR_Operations.Asset_Management import assets, asset_allocation, asset_return, asset_maintenance, asset_insurance
# from routers.Company_Settings import currency, financial_year, localization, policy, company_profile
# from routers.Payroll.salary_slip import router as salary_slip_router
# from routers.Forms_Workflows.approvals import router as approvals_router

# from routers.Forms_Workflows.custom_form_builder import router as custom_form_router


# from routers.Employee_Management.org_hierarchy import router as org_hierarchy_router
# # app.include_router(some_router)
# # app.include_router(other_router)

# # HR Operations - Letters & Exit Management
# from routers.HR_Operations.letter_generation import router as letter_generation
# from routers.HR_Operations.exit_management import router as exit_management
# from routers.Employee_Management.employee_lifecycle import router as employee_lifecycle_router
 
 
# from routers.Payroll.reimbursements import router as reimbursements_router
# from routers.Payroll.loans_advances import router as loans_advances_router



# # CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # STARTUP — CREATE TABLES & DEFAULT SUPERADMIN
# @app.on_event("startup")
# def on_startup():
#     print(">>> STARTUP BEGIN")
#     try:
#         print(">>> Creating SQLModel tables...")
#         SQLModel.metadata.create_all(bind=engine)
#         print(">>> SQLModel done")
#         print(">>> Creating Base tables...")
#         Base.metadata.create_all(bind=engine)
#         print(">>> Base done")
#         print("✓ Database tables initialized successfully")
#     except Exception as e:
#         print(f"⚠ Warning: Could not create database tables: {e}")
#         print("  The application will continue, but database operations may fail.")
#         print("  Please ensure PostgreSQL is running and DATABASE_URL is correct.")
#         return

#     try:
#         print(">>> Checking superadmin...")
#         with Session(engine) as session:
#             superadmin = session.exec(select(User).where(User.role == "superadmin")).first()
#             if not superadmin:
#                 from passlib.context import CryptContext
#                 pwd = CryptContext(schemes=["bcrypt"])
#                 user = User(
#                     name="Super Admin",
#                     username="superadmin",
#                     email="superadmin@example.com",
#                     hashed_password=pwd.hash("admin123"),
#                     role="superadmin",
#                     is_active=True,
#                 )
#                 session.add(user)
#                 session.commit()
#                 print("✓ Default Super Admin created: superadmin / admin123")
#             else:
#                 print("✓ Super Admin already exists")
#     except Exception as e:
#         print(f"⚠ Warning: Could not create default superadmin: {e}")
#         print("  You may need to create it manually once the database is available.")

#     print(">>> STARTUP COMPLETE")


# # SQLADMIN PANEL
# class UserAdmin(ModelView, model=User):
#     column_list = [User.id, User.username, User.email, User.role, User.is_active, User.created_at]
#     form_columns = [User.username, User.email, User.role, User.is_active]
#     name = "User"
#     name_plural = "Users"
#     icon = "fa-solid fa-user"

# admin = Admin(app=app, engine=engine, title="Super Admin Dashboard")
# admin.add_view(UserAdmin)


# # ROUTE REGISTRATION
# app.include_router(auth_router)
# app.include_router(jobs_router)
# app.include_router(admin_router, prefix="/api/admin")
# app.include_router(admin_compat_router)
# app.include_router(candidates_router)
# app.include_router(pipeline_router)
# app.include_router(salary_slip_router)
# app.include_router(recruiter_dashboard_router, prefix="/api/recruiter_dashboard")
# app.include_router(analytics_router)
# app.include_router(assessments_router)
# app.include_router(assignments_router)
# app.include_router(candidates_result_router, prefix="/api/assessment_results")
# app.include_router(ai_interview_router)
# app.include_router(comm_router, prefix="/comm")
# app.include_router(coding_router, prefix="/coding")
# app.include_router(exam.router, prefix="/api/assessment/aptitude")
# app.include_router(aptitude_results.router, prefix="/api/assessment/aptitude")
# app.include_router(hiring_funnel_router, prefix="/api/hiring_funnel")
# app.include_router(time_hire_router, prefix="/api/time_to_hire")
# app.include_router(shift.router, prefix="/attendance/shifts", tags=["Shift Management"])


# app.include_router(documents_router, prefix="/api/documents")
# app.include_router(signatures_router, prefix="/api/signatures")
# app.include_router(onboard_candidates.router, prefix="/api/candidates")
# app.include_router(uploads.router, prefix="/api/uploads")
# app.include_router(tasks_router, prefix="/api/tasks")
# app.include_router(resume_router, prefix="/api/resume")
# app.include_router(interviews.router, prefix="/api/interviews")
# app.include_router(email_router)
# app.include_router(offer_template_router, prefix="/api/offers")
# app.include_router(offer_tracking_router, prefix="/api/offers")

# # CRM Modules
# app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
# app.include_router(company.router, prefix="/companies", tags=["companies"])
# app.include_router(deals.router, prefix="/deals", tags=["deals"])
# app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
# app.include_router(leads.router, prefix="/leads", tags=["leads-legacy"], include_in_schema=False)
# app.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
# app.include_router(activities.router, prefix="/activities", tags=["activities"])
# app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# app.include_router(clients.router)
# app.include_router(projects.router)
# app.include_router(tasks.router)

# # Onboarding Routes
# app.include_router(admin_candidates_router)
# app.include_router(bank_details.router)
# app.include_router(present_address.router)
# app.include_router(statutory.router)
# app.include_router(onboarding.router)
# app.include_router(approval.router)
# app.include_router(employee.router)
# app.include_router(family_details.router)
# app.include_router(documents.router)
# app.include_router(personal_info.router)
# app.include_router(address.router)

# # Company Settings
# app.include_router(currency.router)
# app.include_router(financial_year.router)
# app.include_router(localization.router)
# app.include_router(policy.router)
# app.include_router(company_profile.router)

# # HR Operations - Asset Management
# app.include_router(assets.router)
# app.include_router(asset_allocation.router)
# app.include_router(asset_return.router)
# app.include_router(asset_maintenance.router)
# app.include_router(asset_insurance.router)

# #forms_workflows

# # HR Operations - Letters & Exit Management
# app.include_router(letter_generation)
# app.include_router(exit_management)

# # Forms & Workflows

# app.include_router(approvals_router)
# app.include_router(custom_form_router)


# # Org Hierarchy
# app.include_router(org_hierarchy_router)
# app.include_router(employee_lifecycle_router)

# #payroll managemet
# app.include_router(reimbursements_router)
# app.include_router(loans_advances_router)

# # STATIC FILES
# if not os.path.exists("uploads"):
#     os.makedirs("uploads")

# app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# # TEST ENDPOINT
# @app.get("/api/test")
# def test_api():
#     return {"message": "Backend is working correctly!"} 

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
from contextlib import asynccontextmanager
from core.startup import on_startup

# CREATE FASTAPI APP (THIS MUST COME FIRST)
app = FastAPI(title="AI Recruitment HR Platform")


# IMPORT ROUTERS
from routers.admin_users.auth import router as auth_router
from routers.jobs import router as jobs_router
from routers.admin_users.admin import router as admin_router, compat_router as admin_compat_router
from routers.candidates import router as candidates_router
from routers.admin_users.recruiter_dashboard import router as recruiter_dashboard_router
from routers.pipeline import router as pipeline_router
from routers.Analytics_Dashboard.analytics import router as analytics_router
from routers.HR_Automation.digital_signature.routers.documents import router as documents_router
from routers.HR_Automation.digital_signature.routers.signatures import router as signatures_router
from routers.Candidate_assessments.Assessment.Assessments.assessments_router import router as assessments_router
from routers.Candidate_assessments.Assessment.Assessments.assignments_router import router as assignments_router
from routers.Candidate_assessments.Assessment.Assessments.ai_interview_router import router as ai_interview_router
from routers.Candidate_assessments.Assessment.communication.comm_routes import router as comm_router
from routers.Candidate_assessments.Assessment.coding.coding import router as coding_router
from routers.Candidate_assessments.Assessment.Assessments.Assessment_Result.candidates import router as candidates_result_router
from routers.Candidate_assessments.Assessment.aptitude.routers import exam, results as aptitude_results
from routers.Basic_analytics.hiring_funnel.routers.hiring_funnel import router as hiring_funnel_router
from routers.Basic_analytics.hiring_funnel.routers.hiring_funnel import router as time_hire_router
from routers.HR_Automation.Task_Management.router.tasks_router import router as tasks_router
from routers.Resume_parsing.routers.resume_router import router as resume_router
from routers.admin_users.send_assessment_email import router as email_router
from routers.offers.offer_template_router import router as offer_template_router
from routers.offers.offer_tracking_router import router as offer_tracking_router
from routers.HR_Automation.Onboarding.routers import candidates as onboard_candidates, uploads
from routers.HR_Automation.attendance import attendance_capture, daily_punches, daily_attendance, monthly_attendance, shift_management, manual_attendance, leave_correction, work_hour_rule, leave_management
from routers.AI_Interview_Bot.routes import interviews
from routers.CRM import contacts, company, deals, leads, pipelines, activities, analytics, projects, clients, tasks
from routers.onboarding.admin_candidates import router as admin_candidates_router
from routers.onboarding import bank_details, present_address, statutory, onboarding, approval, employee, family_details, documents, personal_info, address
from routers.HR_Operations.Asset_Management import assets, asset_allocation, asset_return, asset_maintenance, asset_insurance
from routers.Company_Settings import currency, financial_year, localization, policy, company_profile
from routers.Payroll.salary_slip import router as salary_slip_router
from routers.Forms_Workflows.approvals import router as approvals_router
from routers.Forms_Workflows.custom_form_builder import router as custom_form_router
from routers.Employee_Management.org_hierarchy import router as org_hierarchy_router
from routers.HR_Operations.letter_generation import router as letter_generation
from routers.HR_Operations.exit_management import router as exit_management
from routers.Employee_Management.employee_lifecycle import router as employee_lifecycle_router
from routers.Payroll.reimbursements import router as reimbursements_router
from routers.Payroll.loans_advances import router as loans_advances_router


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# STARTUP — CREATE TABLES & DEFAULT SUPERADMIN
@app.on_event("startup")
def on_startup():
    print(">>> STARTUP BEGIN")
    try:
        print(">>> Creating SQLModel tables...")
        SQLModel.metadata.create_all(bind=engine)
        print(">>> SQLModel done")
        print(">>> Creating Base tables...")
        Base.metadata.create_all(bind=engine)
        print(">>> Base done")
        print("✓ Database tables initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not create database tables: {e}")
        print("  The application will continue, but database operations may fail.")
        print("  Please ensure PostgreSQL is running and DATABASE_URL is correct.")
        return

    try:
        print(">>> Checking superadmin...")
        with Session(engine) as session:
            superadmin = session.exec(select(User).where(User.role == "superadmin")).first()
            if not superadmin:
                from passlib.context import CryptContext
                pwd = CryptContext(schemes=["bcrypt"])
                user = User(
                    name="Super Admin",
                    username="superadmin",
                    email="superadmin@example.com",
                    hashed_password=pwd.hash("admin123"),
                    role="superadmin",
                    is_active=True,
                )
                session.add(user)
                session.commit()
                print("✓ Default Super Admin created: superadmin / admin123")
            else:
                print("✓ Super Admin already exists")
    except Exception as e:
        print(f"⚠ Warning: Could not create default superadmin: {e}")
        print("  You may need to create it manually once the database is available.")

    print(">>> STARTUP COMPLETE")


# SQLADMIN PANEL
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.role, User.is_active, User.created_at]
    form_columns = [User.username, User.email, User.role, User.is_active]
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"

admin = Admin(app=app, engine=engine, title="Super Admin Dashboard")
admin.add_view(UserAdmin)


# ROUTE REGISTRATION
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(admin_router, prefix="/api/admin")
app.include_router(admin_compat_router)
app.include_router(candidates_router)
app.include_router(pipeline_router)
app.include_router(salary_slip_router)
app.include_router(recruiter_dashboard_router, prefix="/api/recruiter_dashboard")
app.include_router(analytics_router)
app.include_router(assessments_router)
app.include_router(assignments_router)
app.include_router(candidates_result_router, prefix="/api/assessment_results")
app.include_router(ai_interview_router)
app.include_router(comm_router, prefix="/comm")
app.include_router(coding_router, prefix="/coding")
app.include_router(exam.router, prefix="/api/assessment/aptitude")
app.include_router(aptitude_results.router, prefix="/api/assessment/aptitude")
app.include_router(hiring_funnel_router, prefix="/api/hiring_funnel")
app.include_router(time_hire_router, prefix="/api/time_to_hire")


# Attendance 
app.include_router(attendance_capture.router)
app.include_router(daily_punches.router)
app.include_router(daily_attendance.router)
app.include_router(monthly_attendance.router)
app.include_router(manual_attendance.router)
app.include_router(leave_correction.router)
app.include_router(work_hour_rule.router)
app.include_router(shift_management.router)
app.include_router(leave_management.router)

app.include_router(documents_router, prefix="/api/documents")
app.include_router(signatures_router, prefix="/api/signatures")
app.include_router(onboard_candidates.router, prefix="/api/candidates")
app.include_router(uploads.router, prefix="/api/uploads")
app.include_router(tasks_router, prefix="/api/tasks")
app.include_router(resume_router, prefix="/api/resume")
app.include_router(interviews.router, prefix="/api/interviews")
app.include_router(email_router)
app.include_router(offer_template_router, prefix="/api/offers")
app.include_router(offer_tracking_router, prefix="/api/offers")

# CRM Modules
app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
app.include_router(company.router, prefix="/companies", tags=["companies"])
app.include_router(deals.router, prefix="/deals", tags=["deals"])
app.include_router(leads.router, prefix="/api/leads", tags=["leads"])
app.include_router(leads.router, prefix="/leads", tags=["leads-legacy"], include_in_schema=False)
app.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
app.include_router(activities.router, prefix="/activities", tags=["activities"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(tasks.router)

# Onboarding Routes
app.include_router(admin_candidates_router)
app.include_router(bank_details.router)
app.include_router(present_address.router)
app.include_router(statutory.router)
app.include_router(onboarding.router)
app.include_router(approval.router)
app.include_router(employee.router)
app.include_router(family_details.router)
app.include_router(documents.router)
app.include_router(personal_info.router)
app.include_router(address.router)

# Company Settings
app.include_router(currency.router)
app.include_router(financial_year.router)
app.include_router(localization.router)
app.include_router(policy.router)
app.include_router(company_profile.router)

# HR Operations - Asset Management
app.include_router(assets.router)
app.include_router(asset_allocation.router)
app.include_router(asset_return.router)
app.include_router(asset_maintenance.router)
app.include_router(asset_insurance.router)

# HR Operations - Letters & Exit Management
app.include_router(letter_generation)
app.include_router(exit_management)

# Forms & Workflows
app.include_router(approvals_router)
app.include_router(custom_form_router)

# Employee Management
app.include_router(org_hierarchy_router)
app.include_router(employee_lifecycle_router)

# Payroll Management
app.include_router(reimbursements_router)
app.include_router(loans_advances_router)

# STATIC FILES
if not os.path.exists("uploads"):
    os.makedirs("uploads")

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# TEST ENDPOINT
@app.get("/api/test")
def test_api():
    return {"message": "Backend is working correctly!"}


# ── Lifespan (FastAPI 0.95+) ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    on_startup() runs ONCE when the server boots.
    Seeds default leave types if the table is empty.
    No seeding happens inside individual endpoints.
    """
    on_startup()
    yield