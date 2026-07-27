
from sqlalchemy import text, inspect
from core.database import engine, SessionLocal
from model.onboarding.employee import Employee
from model.Company_Settings.location import CompanyLocation


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_schema_migration():
    with engine.connect() as conn:
        if not _column_exists("employees", "location_id"):
            print("Adding employees.location_id ...")
            conn.execute(text("ALTER TABLE employees ADD COLUMN location_id INTEGER REFERENCES company_locations(id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_employees_location_id ON employees(location_id)"))
            conn.commit()
        else:
            print("employees.location_id already exists — skipping.")


def print_backfill_summary():
    db = SessionLocal()
    try:
        employees_missing = db.query(Employee).filter(Employee.location_id.is_(None)).count()
        print(f"\nEmployees with no location_id (branch) assigned: {employees_missing}")
        if employees_missing:
            print(
                "\nThese employees will show 'No branch assigned' in the UI until "
                "backfilled. Use backfill_employees_by_free_text_location() below if "
                "the legacy employees.location free-text values match a CompanyLocation "
                "name for the same tenant, or assign manually from the UI."
            )
    finally:
        db.close()


def backfill_employees_by_free_text_location():
    """
    Best-effort backfill: for employees that still only have the legacy free-text
    `location` string, try to match it (case-insensitive) against a CompanyLocation
    name belonging to the same tenant and set location_id accordingly.
    Employees with no match, or with tenant_id=None, are left untouched and must be
    assigned a branch manually from the UI.
    """
    db = SessionLocal()
    try:
        updated = 0
        skipped = 0
        employees = (
            db.query(Employee)
            .filter(Employee.location_id.is_(None), Employee.location.isnot(None))
            .all()
        )
        for emp in employees:
            if not emp.tenant_id:
                skipped += 1
                continue
            match = (
                db.query(CompanyLocation)
                .filter(
                    CompanyLocation.tenant_id == emp.tenant_id,
                    CompanyLocation.is_active.is_(True),
                )
                .filter(CompanyLocation.name.ilike(emp.location.strip()))
                .first()
            )
            if match:
                emp.location_id = match.id
                updated += 1
            else:
                skipped += 1
        db.commit()
        print(f"Backfilled {updated} employee(s) by matching free-text location -> branch.")
        print(f"Skipped {skipped} employee(s) — no matching branch name found; assign manually.")
    finally:
        db.close()


if __name__ == "__main__":
    run_schema_migration()
    print_backfill_summary()
    print(
        "\nSchema migration complete. Optionally call "
        "backfill_employees_by_free_text_location() from a Python shell to auto-match "
        "existing free-text locations to real branch records."
    )
