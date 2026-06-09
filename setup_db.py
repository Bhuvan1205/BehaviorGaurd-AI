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

    db_name = os.getenv("DB_NAME", "behavior_guard_ai")

    for file_path in sql_files:
        print(f"Executing {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()
            # Ignore CREATE DATABASE
            sql = sql.replace("CREATE DATABASE behavior_guard_ai;", "-- CREATE DATABASE behavior_guard_ai;")

        # Split into individual statements
        statements = sql.split(";")
        success_count = 0
        ignored_count = 0

        for stmt in statements:
            stmt_clean = stmt.strip()
            if not stmt_clean:
                continue

            # Replace database name reference in SQL statements (like GRANT CONNECT ON DATABASE)
            stmt_clean = stmt_clean.replace("behavior_guard_ai", db_name)

            try:
                cur.execute(stmt_clean)
                success_count += 1
            except Exception as e:
                err_msg = str(e).lower()
                # Ignore expected warnings when running on cloud databases (e.g. Supabase, Neon)
                if any(x in err_msg for x in ["already exists", "permission denied", "must be superuser", "role", "grant", "connect", "empty query"]):
                    ignored_count += 1
                else:
                    print(f"❌ Critical error on statement: {stmt_clean[:150]}...")
                    print(e)
                    raise e

        print(f"✅ Finished executing {os.path.basename(file_path)}: {success_count} statements succeeded, {ignored_count} non-critical warnings ignored.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    setup_db()
