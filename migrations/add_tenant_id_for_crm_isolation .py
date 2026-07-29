from sqlalchemy import text, inspect
from core.database import engine

CRM_TABLES = ["activities", "clients", "contacts", "deals", "leads", "pipelines", "projects", "tasks"]


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return True  # table doesn't exist yet, nothing to migrate — skip quietly
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def run_schema_migration():
    with engine.connect() as conn:
        for table in CRM_TABLES:
            if not _column_exists(table, "tenant_id"):
                print(f"Adding {table}.tenant_id ...")
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN tenant_id INTEGER"))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_tenant_id ON {table}(tenant_id)"))
                conn.commit()
            else:
                print(f"{table}.tenant_id already exists — skipping.")


if __name__ == "__main__":
    run_schema_migration()
    print(
        "\nDone. IMPORTANT: existing rows in these 8 tables will have "
        "tenant_id = NULL — meaning they currently belong to no company and "
        "won't show up once the CRM routers start filtering by tenant_id "
        "(leads/deals/contacts/clients are wired up already; activities, "
        "projects, tasks, pipelines, company still need the same treatment "
        "on the router/crud side). If you have real CRM data already in the "
        "database, you'll want to backfill tenant_id on those rows manually "
        "before relying on this filter, or they'll become invisible."
    )