import pymysql
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
SQL_PATH = ROOT / "database" / "sql" / "create_database.sql"

load_dotenv(BACKEND_DIR / ".env")

url = make_url(os.environ.get("DATABASE_URL", "mysql+pymysql://root:password@localhost:3306/ecommerce_db"))
host = url.host or "127.0.0.1"
port = url.port or 3306
username = url.username or "root"
password = url.password or ""
database = url.database or "ecommerce_db"

print(f"Creating database '{database}' on {host}:{port}...")

try:
    connection = pymysql.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        charset='utf8mb4'
    )

    with connection.cursor() as cursor:
        sql = SQL_PATH.read_text(encoding="utf-8").format(database=database.replace("`", "``"))
        cursor.execute(sql)
        connection.commit()
        print(f"[OK] Database '{database}' created successfully")

    connection.close()
except Exception as e:
    print(f"[ERROR] Error creating database: {e}")
    raise
