import sys
sys.path.insert(0, '.')
from app.api.db import get_connection
import psycopg2
from psycopg2.extras import RealDictCursor

conn = get_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check columns
cur.execute(
    "SELECT column_name, data_type FROM information_schema.columns "
    "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
    ('features', 'user_behavior_features')
)
rows = cur.fetchall()
print('=== features.user_behavior_features columns in Supabase ===')
for r in rows:
    print(f"  {r['column_name']} ({r['data_type']})")

# Check if it's partitioned
cur.execute(
    "SELECT c.relkind FROM pg_class c "
    "JOIN pg_namespace n ON n.oid = c.relnamespace "
    "WHERE n.nspname = %s AND c.relname = %s",
    ('features', 'user_behavior_features')
)
rel = cur.fetchone()
if rel:
    kind = rel['relkind']
    print(f"\nTable relkind: '{kind}' (p=partitioned, r=regular table)")
else:
    print("\nTable not found in pg_class!")

cur.close()
conn.close()
