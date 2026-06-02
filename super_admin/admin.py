# app/admin.py
from sqladmin import Admin, ModelView
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from core.database import engine, get_db
from model import User
from routers.admin_users.auth import get_current_user
from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
import os

# MAIL CONFIG (reuse same env vars as in auth.py)
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("EMAIL_USER"),
    MAIL_PASSWORD=os.getenv("EMAIL_PASS"),
    MAIL_FROM=os.getenv("EMAIL_USER"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True
)


# ROLE CHECK (Only Super Admins can access /admin)
def super_admin_only(current_user=Depends(get_current_user)):
    if not current_user or getattr(current_user, "role", None).lower() != "superadmin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access only")
    return current_user


# USER ADMIN DASHBOARD
class UserAdmin(ModelView, model=User):
    # --- Columns displayed in list view ---
    column_list = [User.id, User.username, User.email, User.role, User.is_active, User.created_at]

    # --- Editable fields ---
    form_columns = [User.username, User.email, User.role, User.is_active]

    # --- Searchable and sortable ---
    column_searchable_list = [User.username, User.email, User.role]
    column_sortable_list = [User.id, User.created_at]

    # --- Enable delete (optional) ---
    can_delete = True

    # --- Nice label ---
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-user"


    #  Add sidebar badge showing pending users
 
    async def get_badge(self, request: Request):
        async with request.state.sessionmaker() as session:
            result = await session.execute(select(func.count()).where(User.is_active == False))
            count = result.scalar_one()
            return str(count) if count > 0 else None


    #  Auto email when user is activated
  
    async def after_model_change(self, data, model, is_created, request: Request):
        # Only act if user activation changed from inactive to active
        if not is_created and getattr(model, "is_active", False):
            fm = FastMail(conf)
            message = MessageSchema(
                subject="Your Account Has Been Activated",
                recipients=[model.email],
                body=f"""
Hi {model.username or model.name},

Your account has been activated by the Super Admin.
You can now log in and start using the platform.

Login URL: http://localhost:3000/login

Best Regards,
HR Automation System
""",
                subtype=MessageType.plain,
            )
            try:
                await fm.send_message(message)
            except Exception as e:
                print(f"[WARN] Failed to send activation email to {model.email}: {e}")

        return await super().after_model_change(data, model, is_created, request)

# INITIALIZE ADMIN
admin = Admin(
    app=None,       # will bind later in main.py
    engine=engine,
    title="Super Admin Dashboard",
)


# REGISTER VIEWS
def register_admin_views():
    admin.add_view(UserAdmin)
