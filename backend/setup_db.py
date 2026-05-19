import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Direct configuration
host = "127.0.0.1"
port = 3306
username = "root"
password = "20041122"
database = "ecommerce_db"

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
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        connection.commit()
        print(f"[OK] Database '{database}' created successfully")

    connection.close()
except Exception as e:
    print(f"[ERROR] Error creating database: {e}")
    raise
