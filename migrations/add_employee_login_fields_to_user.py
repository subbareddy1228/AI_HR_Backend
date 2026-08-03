from sqlalchemy import text, inspect
from core.database import engine


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_schema_migration():
    with engine.connect() as conn:
        if not _column_exists("user", "employee_id"):
            print('Adding "user".employee_id ...')
            conn.execute(text('ALTER TABLE "user" ADD COLUMN employee_id INTEGER'))
            conn.execute(text('CREATE INDEX IF NOT EXISTS ix_user_employee_id ON "user"(employee_id)'))
            conn.commit()
        else:
            print('"user".employee_id already exists — skipping.')

        if not _column_exists("user", "requires_password_change"):
            print('Adding "user".requires_password_change ...')
            conn.execute(
                text(
                    'ALTER TABLE "user" ADD COLUMN requires_password_change '
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            conn.commit()
        else:
            print('"user".requires_password_change already exists — skipping.')


if __name__ == "__main__":
    run_schema_migration()
    print("Done.")