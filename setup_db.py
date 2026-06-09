import psycopg2
import glob
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def setup_db():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "behavior_guard_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433")
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
