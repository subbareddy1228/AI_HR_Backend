
from sqlalchemy import text, inspect
from core.database import engine, SessionLocal
from model.models import User
from model.onboarding.employee import Employee
from model.Company_Settings.location import CompanyLocation  # noqa: F401 — needed for Employee.branch relationship to resolve


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_schema_migration():
    with engine.connect() as conn:
        if not _column_exists("user", "tenant_id"):
            print('Adding "user".tenant_id ...')
            conn.execute(text('ALTER TABLE "user" ADD COLUMN tenant_id INTEGER'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_user_tenant_id ON "user"(tenant_id)'))
            conn.commit()
        else:
            print('"user".tenant_id already exists — skipping.')

        if not _column_exists("employees", "tenant_id"):
            print("Adding employees.tenant_id ...")
            conn.execute(text("ALTER TABLE employees ADD COLUMN tenant_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_employees_tenant_id ON employees(tenant_id)"))
            conn.commit()
        else:
            print("employees.tenant_id already exists — skipping.")


def print_backfill_summary():
    db = SessionLocal()
    try:
        users_missing = db.query(User).filter(User.tenant_id.is_(None)).count()
        employees_missing = db.query(Employee).filter(Employee.tenant_id.is_(None)).count()
        print(f"\nUsers with no tenant_id:     {users_missing}")
        print(f"Employees with no tenant_id: {employees_missing}")
        if users_missing or employees_missing:
            print(
                "\nThese rows will be invisible under the new tenant-scoped queries "
                "until backfilled. See backfill_employees_by_mapping() below — fill "
                "in a real company_name -> tenant_id mapping for your data before "
                "deploying this to production."
            )
    finally:
        db.close()


def backfill_users_by_company_name(company_to_tenant_id: dict):

    db = SessionLocal()
    try:
        for company_name, tenant_id in company_to_tenant_id.items():
            updated = (
                db.query(User)
                .filter(User.company_name == company_name, User.tenant_id.is_(None))
                .update({"tenant_id": tenant_id})
            )
            print(f"Backfilled {updated} user(s) for '{company_name}' -> tenant_id={tenant_id}")
        db.commit()
    finally:
        db.close()


def backfill_employees_by_mapping(employee_id_to_tenant_id: dict):

    db = SessionLocal()
    try:
        for employee_id, tenant_id in employee_id_to_tenant_id.items():
            updated = (
                db.query(Employee)
                .filter(Employee.id == employee_id, Employee.tenant_id.is_(None))
                .update({"tenant_id": tenant_id})
            )
            if updated:
                print(f"Backfilled employee id={employee_id} -> tenant_id={tenant_id}")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run_schema_migration()
    print_backfill_summary()
    print(
        "\nSchema migration complete. Call backfill_users_by_company_name(...) and/or "
        "backfill_employees_by_mapping(...) from a Python shell with your real mapping "
        "before relying on tenant-scoped queries against existing data."
    )