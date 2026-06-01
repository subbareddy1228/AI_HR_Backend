# Backend – Folder Structure & Request Flow

## High-level request flow

```
Client (React, localhost:3000)
    → HTTP request (e.g. POST /api/resume/process, GET /contacts, ...)
    → CORS middleware (allows localhost:3000)
    → FastAPI app (main.py)
    → Router (e.g. routers/CRM/activities.py, routers/Resume_parsing/...)
    → Optional: get_current_user (JWT from core/dependencies)
    → Optional: get_db (DB session from core/database)
    → Business logic: schema (Pydantic) + crud_ops or service layer + model (ORM)
    → Response (JSON / file) back to client
```

---

## Folder structure

```
Backend/
├── main.py                    # FastAPI app, CORS, router includes, startup (DB + superadmin)
├── .env                       # DATABASE_URL, SECRET_KEY, OPENAI_API_KEY, SMTP, etc.
│
├── core/                      # App core
│   ├── config.py              # Settings from .env (pydantic_settings)
│   ├── database.py            # SQLAlchemy engine, SessionLocal, get_db
│   └── dependencies.py        # get_current_user (JWT), require_roles
│
├── model/                     # ORM / SQLAlchemy models (database tables)
│   ├── models.py              # User, Job, Candidate, Application, CandidateRecord, etc.
│   ├── contact.py, deal.py, company.py, activity.py, lead.py, pipeline.py, ...
│   ├── onboarding/            # Onboarding-related models
│   ├── HR_Operations/Asset_Management/
│   └── Company_Settings/
│
├── schema/                    # Pydantic request/response schemas (validation, serialization)
│   ├── __init__ .py           # Re-exports
│   ├── activity.py, contact.py, deal.py, assessment.py, ai_interview.py, ...
│   ├── onboarding/
│   ├── Company_Settings/
│   └── HR_Operations/Asset_Management/
│
├── crud_ops/                  # Database operations (CRUD) used by many routers
│   └── crud.py                # create_*, get_*, update_*, delete_* for contacts, deals, activities, jobs, etc.
│
├── services/                  # Business logic layer (used by some routers)
│   ├── jobs_service.py, candidates_service.py, employee_service.py, ...
│   ├── Company_Settings/
│   └── ...
│
├── routers/                   # API route handlers (by feature)
│   ├── admin_users/           # auth, admin, recruiter_dashboard, send_assessment_email
│   ├── jobs/                  # job CRUD, search, update, delete
│   ├── candidates/            # candidates API
│   ├── pipeline/              # pipeline stages, candidates
│   ├── CRM/                   # contacts, company, deals, leads, pipelines, activities, analytics, projects, clients, tasks
│   ├── Resume_parsing/        # AI resume screening
│   │   └── routers/           # resume_router.py, utils.py (OpenAI), config.py
│   ├── Candidate_assessments/ # Assessments, assignments, AI interview, aptitude, coding, communication
│   ├── AI_Interview_Bot/      # interviews routes
│   ├── HR_Automation/         # digital_signature, Task_Management, Onboarding, attendance, leave
│   ├── HR_Operations/Asset_Management/
│   ├── Company_Settings/      # currency, financial_year, localization, policy, company_profile
│   ├── onboarding/           # bank_details, present_address, statutory, onboarding, approval, employee, family_details, documents, personal_info, address
│   ├── offers/                # offer_template_router, offer_tracking_router
│   ├── Analytics_Dashboard/   # analytics
│   └── Basic_analytics/       # hiring_funnel, time_to_hire
│
├── utils/                     # Shared helpers (validators, dates, file_utils, response, etc.)
├── super_admin/               # Super admin auth and admin logic
├── templat/                   # Scripts (migrations, init questions, fix tables, etc.)
└── uploads/                   # Static uploads (mounted at /uploads in main.py)
```

---

## How a typical request is handled

1. **Entry (main.py)**  
   - Request hits FastAPI app.  
   - CORS middleware allows `http://localhost:3000` (and others).  
   - Request is routed by path (e.g. `/api/resume/process` → `resume_router`, `/activities` → CRM `activities`).

2. **Router (e.g. `routers/CRM/activities.py`)**  
   - Defines endpoints (GET/POST/PUT/DELETE).  
   - Uses **Depends(get_db)** for a DB session and optionally **Depends(get_current_user)** for JWT auth.  
   - Reads request body/query and validates with **schema** (Pydantic) if applicable.

3. **Data layer**  
   - **schema**: Pydantic models for request/response (e.g. `ActivityCreate`, `Activity`).  
   - **crud_ops/crud.py** or **services/** : functions that take `db` and perform queries/updates.  
   - **model**: SQLAlchemy/SQLModel table definitions (e.g. `model.Activity`).

4. **Response**  
   - Router returns a Pydantic model or dict; FastAPI serializes to JSON.  
   - For errors, routers raise **HTTPException** (e.g. 400, 401, 404, 503); these still get CORS headers.

---

## Important paths (from main.py)

| Prefix / path        | Purpose / router |
|----------------------|------------------|
| `/api/auth/...`      | Auth (login, etc.) |
| `/api/admin`         | Admin APIs |
| `/api/recruiter_dashboard` | Recruiter dashboard |
| `/api/resume`        | Resume parsing / AI screening |
| `/api/assessment/aptitude` | Aptitude exam & results |
| `/api/interviews`    | AI interview bot |
| `/api/offers`        | Offer template & tracking |
| `/api/attendance`, `/api/leave` | Attendance & leave |
| `/api/tasks`         | Task management |
| `/contacts`, `/deals`, `/activities`, `/companies`, `/leads`, `/pipelines`, `/analytics`, ... | CRM |
| `/uploads`           | Static files (uploaded files) |
| `/admin`             | SQLAdmin panel (User management) |

---

## Database and config

- **DB**: Configured in **core/database.py** via `core.config.settings.DATABASE_URL` (from `.env`).  
- **Session**: `get_db()` yields a SQLAlchemy `Session`; used as `Depends(get_db)` in routers.  
- **Auth**: JWT in **core/dependencies.py** (`get_current_user`, `require_roles`).  
- **Startup (main.py)**: Creates tables and a default superadmin user if none exists.

This is the backend flow and folder structure for the AI & HR, CRM, HRMS project.
