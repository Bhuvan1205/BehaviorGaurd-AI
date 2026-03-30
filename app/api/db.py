import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        dbname="behavior_guard_ai",   # ✅ FIXED NAME
        user="postgres",              # 🔁 update if needed
        password="Bhuvan2005!",          # 🔁 update
        host="localhost",
        port="5432"
    )


def get_cursor():
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=RealDictCursor)