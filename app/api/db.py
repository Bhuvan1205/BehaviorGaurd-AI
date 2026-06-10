import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def get_connection():
    # Supabase's PgBouncer pooler (port 6543) requires SSL.
    # sslmode=require ensures the handshake completes without hanging.
    # statement_timeout guards against runaway queries on the DB side.
    host = os.getenv("DB_HOST", "localhost")
    sslmode = "require" if "supabase.com" in host else "prefer"
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "behavior_guard_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=host,
        port=os.getenv("DB_PORT", "5433"),
        connect_timeout=10,
        sslmode=sslmode,
        options="-c statement_timeout=25000",
    )


def get_cursor():
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=RealDictCursor)