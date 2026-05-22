# SQL Files

This directory keeps project-maintained SQL outside Python code.

## Files

- `create_database.sql`
  - Used by `backend/setup_db.py`.
  - Creates the MySQL database/schema if it does not already exist.

- `alter_finance_category_enum.sql`
  - Used by `backend/_alter_finance_category.py`.
  - Extends `finance_records.category` enum values.

- `reset_business_data.sql`
  - Manual maintenance SQL for clearing demo business data while keeping account and permission tables.

## Rule

When SQL changes are needed, add or update a `.sql` file here and keep Python scripts as thin executors.
