from sqlalchemy import text, inspect
from core.database import engine


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_schema_migration():
    with engine.connect() as conn:
        if not _column_exists("user", "profile_completed"):
            print('Adding "user".profile_completed ...')
            conn.execute(
                text(
                    'ALTER TABLE "user" ADD COLUMN profile_completed '
                    "BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            conn.commit()
        else:
            print('"user".profile_completed already exists — skipping.')


if __name__ == "__main__":
    run_schema_migration()
    print("Done.")