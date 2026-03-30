import psycopg2
import glob
import os

def setup_db():
    conn = psycopg2.connect(
        dbname="behavior_guard_ai",
        user="postgres",
        password="Bhuvan2005!",
        host="localhost",
        port="5432"
    )
    conn.autocommit = True
    cur = conn.cursor()

    sql_files = sorted(glob.glob("Database/DB M*.sql"))
    print(f"Found SQL files: {sql_files}")

    for file_path in sql_files:
        print(f"Executing {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()
            # Ignore CREATE DATABASE since docker handles it
            sql = sql.replace("CREATE DATABASE behavior_guard_ai;", "-- CREATE DATABASE behavior_guard_ai;")
        try:
            cur.execute(sql)
            print(f"✅ Successfully executed {os.path.basename(file_path)}")
        except Exception as e:
            print(f"❌ Error executing {os.path.basename(file_path)}:")
            print(e)
            break

    cur.close()
    conn.close()

if __name__ == "__main__":
    setup_db()
