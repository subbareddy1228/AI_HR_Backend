-- One-time fix for production: the `user` table predates the
-- employee_id / requires_password_change / profile_completed columns
-- that model/models.py::User now defines. Base.metadata.create_all()
-- (used in main.py) only creates missing tables — it never alters an
-- existing one — so these were never added to the live database.
--
-- Safe to run more than once (IF NOT EXISTS guards). Run this once
-- against the Render Postgres instance (Render dashboard -> your
-- Postgres -> Connect -> psql, or any Postgres client using the
-- DATABASE_URL from your Render env vars).

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS employee_id INTEGER;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS requires_password_change BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS profile_completed BOOLEAN NOT NULL DEFAULT false;

-- Sanity check: confirm all three now exist.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'user'
  AND column_name IN ('employee_id', 'requires_password_change', 'profile_completed');\q