# """
# Migration: Create Salary Structure Tables
# Run this file directly to create tables in PostgreSQL via pgAdmin or psycopg2.
# """

# import psycopg2

# DB_CONFIG = {
#     "host": "localhost",
#     "database": "ai_hr_db",       # <-- change to your DB name
#     "user": "postgres",            # <-- change to your DB user
#     "password": "yourpassword",    # <-- change to your DB password
#     "port": 5432,
# }

# SQL = """
# -- ENUM types
# DO $$ BEGIN
#     CREATE TYPE componenttype AS ENUM ('earning', 'deduction', 'statutory');
# EXCEPTION WHEN duplicate_object THEN NULL;
# END $$;

# DO $$ BEGIN
#     CREATE TYPE calculationtype AS ENUM ('fixed', 'percentage', 'formula');
# EXCEPTION WHEN duplicate_object THEN NULL;
# END $$;

# -- Salary Structures Table
# CREATE TABLE IF NOT EXISTS salary_structures (
#     id               SERIAL PRIMARY KEY,
#     name             VARCHAR(100) NOT NULL UNIQUE,
#     description      TEXT,
#     is_active        BOOLEAN DEFAULT TRUE,
#     created_at       TIMESTAMPTZ DEFAULT NOW(),
#     updated_at       TIMESTAMPTZ
# );

# -- Salary Components Table
# CREATE TABLE IF NOT EXISTS salary_components (
#     id               SERIAL PRIMARY KEY,
#     structure_id     INTEGER NOT NULL REFERENCES salary_structures(id) ON DELETE CASCADE,
#     name             VARCHAR(100) NOT NULL,
#     code             VARCHAR(20) NOT NULL,
#     component_type   componenttype NOT NULL,
#     calculation_type calculationtype NOT NULL DEFAULT 'fixed',
#     value            FLOAT NOT NULL DEFAULT 0.0,
#     formula          TEXT,
#     depends_on       VARCHAR(50),
#     is_taxable       BOOLEAN DEFAULT FALSE,
#     is_active        BOOLEAN DEFAULT TRUE,
#     sequence         INTEGER DEFAULT 1,
#     created_at       TIMESTAMPTZ DEFAULT NOW(),
#     updated_at       TIMESTAMPTZ
# );

# -- Employee Salary Structure Assignments
# CREATE TABLE IF NOT EXISTS employee_salary_structures (
#     id               SERIAL PRIMARY KEY,
#     employee_id      INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
#     structure_id     INTEGER NOT NULL REFERENCES salary_structures(id) ON DELETE CASCADE,
#     ctc              FLOAT NOT NULL,
#     basic_salary     FLOAT NOT NULL,
#     effective_from   TIMESTAMPTZ NOT NULL,
#     effective_to     TIMESTAMPTZ,
#     is_active        BOOLEAN DEFAULT TRUE,
#     created_at       TIMESTAMPTZ DEFAULT NOW(),
#     updated_at       TIMESTAMPTZ
# );

# -- Indexes for performance
# CREATE INDEX IF NOT EXISTS idx_salary_components_structure_id ON salary_components(structure_id);
# CREATE INDEX IF NOT EXISTS idx_emp_salary_structure_employee_id ON employee_salary_structures(employee_id);
# CREATE INDEX IF NOT EXISTS idx_emp_salary_structure_active ON employee_salary_structures(employee_id, is_active);
# """


# def run_migration():
#     try:
#         conn = psycopg2.connect(**DB_CONFIG)
#         cursor = conn.cursor()
#         cursor.execute(SQL)
#         conn.commit()
#         cursor.close()
#         conn.close()
#         print("✅ Salary Structure tables created successfully.")
#     except Exception as e:
#         print(f"❌ Migration failed: {e}")


# if __name__ == "__main__":
#     run_migration()







"""
Migration: Create Salary Structure Tables
Run this file directly to create tables in PostgreSQL via pgAdmin or psycopg2.
"""

import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "database": "ai_hr_db",       # <-- change to your DB name
    "user": "postgres",            # <-- change to your DB user
    "password": "yourpassword",    # <-- change to your DB password
    "port": 5432,
}

SQL = """
-- ENUM types
DO $$ BEGIN
    CREATE TYPE componenttype AS ENUM ('earning', 'deduction', 'statutory');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE calculationtype AS ENUM ('fixed', 'percentage', 'formula');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Salary Structures Table
CREATE TABLE IF NOT EXISTS salary_structures (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(100) NOT NULL UNIQUE,
    description      TEXT,
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ
);

-- Salary Components Table
CREATE TABLE IF NOT EXISTS salary_components (
    id               SERIAL PRIMARY KEY,
    structure_id     INTEGER NOT NULL REFERENCES salary_structures(id) ON DELETE CASCADE,
    name             VARCHAR(100) NOT NULL,
    code             VARCHAR(20) NOT NULL,
    component_type   componenttype NOT NULL,
    calculation_type calculationtype NOT NULL DEFAULT 'fixed',
    value            FLOAT NOT NULL DEFAULT 0.0,
    formula          TEXT,
    depends_on       VARCHAR(50),
    is_taxable       BOOLEAN DEFAULT FALSE,
    is_active        BOOLEAN DEFAULT TRUE,
    sequence         INTEGER DEFAULT 1,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ
);

-- Employee Salary Structure Assignments
CREATE TABLE IF NOT EXISTS employee_salary_structures (
    id               SERIAL PRIMARY KEY,
    employee_id      INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    structure_id     INTEGER NOT NULL REFERENCES salary_structures(id) ON DELETE CASCADE,
    ctc              FLOAT NOT NULL,
    basic_salary     FLOAT NOT NULL,
    effective_from   TIMESTAMPTZ NOT NULL,
    effective_to     TIMESTAMPTZ,
    is_active        BOOLEAN DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_salary_components_structure_id ON salary_components(structure_id);
CREATE INDEX IF NOT EXISTS idx_emp_salary_structure_employee_id ON employee_salary_structures(employee_id);
CREATE INDEX IF NOT EXISTS idx_emp_salary_structure_active ON employee_salary_structures(employee_id, is_active);
"""


def run_migration():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(SQL)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Salary Structure tables created successfully.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")


if __name__ == "__main__":
    run_migration()
