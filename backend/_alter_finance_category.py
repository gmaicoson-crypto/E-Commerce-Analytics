"""One-off migration: extend finance_records.category ENUM.

SQL lives in database/sql/alter_finance_category_enum.sql so schema changes are
maintained as standalone SQL instead of embedded Python strings.

Usage:
    cd backend
    python _alter_finance_category.py
"""
from pathlib import Path

from sqlalchemy import text

from database import engine


ROOT = Path(__file__).resolve().parent.parent
SQL_PATH = ROOT / "database" / "sql" / "alter_finance_category_enum.sql"


def main():
    sql = SQL_PATH.read_text(encoding="utf-8")
    with engine.begin() as conn:
        print(f"[alter] executing {SQL_PATH}")
        conn.execute(text(sql))
        print("[alter] done.")


if __name__ == "__main__":
    main()
