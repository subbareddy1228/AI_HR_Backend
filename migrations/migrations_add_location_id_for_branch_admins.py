from sqlalchemy import text, inspect
from core.database import engine


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_schema_migration():
    with engine.connect() as conn:
        if not _column_exists("users", "location_id"):
            print("Adding users.location_id ...")
            conn.execute(text("ALTER TABLE users ADD COLUMN location_id INTEGER REFERENCES company_locations(id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_location_id ON users(location_id)"))
            conn.commit()
        else:
            print("users.location_id already exists — skipping.")


if __name__ == "__main__":
    run_schema_migration()
    print(
        "\nDone. Existing 'admin' users will have location_id = NULL, meaning "
        "they keep whole-company access until a superadmin explicitly assigns "
        "them a branch from Super Admin -> User Management."
    )