import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_connections():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "behavior_guard_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433")
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    print("Checking ALL connections...")
    cur.execute("""
        SELECT pid, usename, state, wait_event_type, wait_event, query
        FROM pg_stat_activity
        WHERE pid != pg_backend_pid();
    """)
    rows = cur.fetchall()
    for row in rows:
        print(row)
        
    print("\nAttempting to terminate ALL other connections to this database...")
    cur.execute("""
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE pid != pg_backend_pid();
    """)
    print("Terminated.")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_connections()
