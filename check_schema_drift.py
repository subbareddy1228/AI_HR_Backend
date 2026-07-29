"""
check_schema_drift.py

Compares the SQLAlchemy/SQLModel models in this project against the actual
live database schema, and reports (or optionally applies) any ADD COLUMN
statements needed to bring the DB in line with the models.

This only ever ADDS missing columns. It never drops or alters existing
columns, so it's safe to run against production.

Usage:
    # Just show what's missing (safe, read-only):
    python check_schema_drift.py

    # Show AND apply the missing columns:
    python check_schema_drift.py --apply

Run this from the project root, with the same venv / .env you use to run
the app (it reads DATABASE_URL the same way main.py does).
"""

import argparse
import importlib
import pkgutil
import sys

from sqlalchemy import inspect, text

# Make sure project root is on the path
sys.path.insert(0, ".")

import model  # noqa: F401  (imports the package so we can walk it)
from core.database import Base, engine


def import_all_submodules(package):
    """Recursively import every module under `package` so every
    SQLAlchemy/SQLModel model class gets registered on Base.metadata."""
    for _, name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        try:
            importlib.import_module(name)
        except Exception as e:
            print(f"  (skipped {name}: {e})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Actually run the ALTER TABLE statements")
    args = parser.parse_args()

    print("Importing all model modules...")
    import_all_submodules(model)

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    statements = []

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            print(f"[NEW TABLE] '{table_name}' does not exist in the DB at all "
                  f"(create_all() should make this — will not touch it here)")
            continue

        db_columns = {col["name"] for col in inspector.get_columns(table_name)}
        model_columns = {col.name: col for col in table.columns}

        missing = set(model_columns.keys()) - db_columns
        for col_name in missing:
            col = model_columns[col_name]
            col_type = col.type.compile(dialect=engine.dialect)
            nullable = "NULL" if col.nullable else "NOT NULL"

            # Only add as nullable initially, even if model says NOT NULL,
            # to avoid failing on existing rows. You can tighten it after
            # backfilling data if needed.
            stmt = f'ALTER TABLE "{table_name}" ADD COLUMN {col_name} {col_type};'
            statements.append((table_name, col_name, stmt))

    if not statements:
        print("\n✅ No missing columns found. DB schema matches your models.")
        return

    print(f"\nFound {len(statements)} missing column(s):\n")
    for table_name, col_name, stmt in statements:
        print(f"  {table_name}.{col_name}")
        print(f"    {stmt}")

    if args.apply:
        print("\nApplying...")
        with engine.begin() as conn:
            for table_name, col_name, stmt in statements:
                print(f"  Running: {stmt}")
                conn.execute(text(stmt))
        print("\n✅ Done. All missing columns added.")
    else:
        print("\nRun again with --apply to actually add these columns.")


if __name__ == "__main__":
    main()