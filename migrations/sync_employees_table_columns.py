"""
Diagnostic + fix-all script for schema drift on the `employees` table.

Compares every column the `Employee` SQLAlchemy model declares against what
actually exists on the live `employees` table, and ALTERs the table to add
whatever is missing — in one pass, instead of discovering them one at a time
via runtime errors.

All added columns are created as NULLable (regardless of what the model
says) so this never fails on a table that already has rows — required /
NOT NULL constraints, if actually desired, should be added as a deliberate
follow-up once the columns are backfilled.

Safe to re-run: only adds columns that are actually missing.
"""

from sqlalchemy import text, inspect
from core.database import engine
from model.onboarding.employee import Employee
from model.Company_Settings.location import CompanyLocation  # noqa: F401 — needed for Employee.branch relationship to resolve


def find_missing_columns() -> list[str]:
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("employees")}
    model_columns = {col.name for col in Employee.__table__.columns}
    return sorted(model_columns - existing)


def run():
    missing = find_missing_columns()

    if not missing:
        print("No schema drift found — employees table already matches the Employee model.")
        return

    print(f"Found {len(missing)} column(s) missing from the live `employees` table:")
    for name in missing:
        print(f"  - {name}")
    print()

    dialect = engine.dialect
    with engine.connect() as conn:
        for name in missing:
            col = Employee.__table__.columns[name]
            col_type = col.type.compile(dialect=dialect)

            ddl = f'ALTER TABLE employees ADD COLUMN "{name}" {col_type}'

            if col.foreign_keys:
                fk = next(iter(col.foreign_keys))
                ddl += f" REFERENCES {fk.column.table.name}({fk.column.name})"

            print(f"Running: {ddl}")
            conn.execute(text(ddl))

            if col.unique:
                idx_name = f"ix_employees_{name}_unique"
                try:
                    conn.execute(
                        text(f'CREATE UNIQUE INDEX IF NOT EXISTS "{idx_name}" ON employees("{name}")')
                    )
                except Exception as e:
                    print(f"  (skipped unique index on {name} — likely duplicate existing values: {e})")
                    conn.rollback()
                    continue
            elif col.index:
                idx_name = f"ix_employees_{name}"
                conn.execute(
                    text(f'CREATE INDEX IF NOT EXISTS "{idx_name}" ON employees("{name}")')
                )

            conn.commit()

    print("\nDone. Re-run this script anytime to check for further drift — it's idempotent.")


if __name__ == "__main__":
    run()