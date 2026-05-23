import pymysql

print("Testing MySQL connection...")

try:
    connection = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="20041122",
        charset="utf8mb4",
        connect_timeout=5,
    )
    print("SUCCESS! Connected to MySQL")

    with connection.cursor() as cursor:
        cursor.execute("SHOW DATABASES")
        databases = cursor.fetchall()
        print("Available databases:")
        for db in databases:
            print(f"  - {db[0]}")

    connection.close()
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")

    # Try with localhost
    print("\nTrying with 'localhost'...")
    try:
        connection = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password="20041122",
            charset="utf8mb4",
            connect_timeout=5,
        )
        print("SUCCESS with localhost!")
        connection.close()
    except Exception as e2:
        print(f"Also failed: {type(e2).__name__}: {e2}")
