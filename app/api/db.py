import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "behavior_guard_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433")
    )


def get_cursor():
    conn = get_connection()
    return conn, conn.cursor(cursor_factory=RealDictCursor)