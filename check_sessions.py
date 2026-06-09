import sys
sys.path.insert(0, '.')
from app.api.db import get_connection
from psycopg2.extras import RealDictCursor

conn = get_connection()
cur = conn.cursor(cursor_factory=RealDictCursor)

# Check admin_sessions
cur.execute("SELECT COUNT(*) as cnt FROM security.admin_sessions WHERE is_active = TRUE AND expires_at > CURRENT_TIMESTAMP")
row = cur.fetchone()
print(f"Active valid sessions: {row['cnt']}")

cur.execute("SELECT COUNT(*) as cnt FROM security.admin_sessions")
row = cur.fetchone()
print(f"Total sessions: {row['cnt']}")

cur.execute("SELECT COUNT(*) as cnt FROM security.admin_users")
row = cur.fetchone()
print(f"Admin users: {row['cnt']}")

cur.execute("SELECT username, expires_at, is_active FROM security.admin_sessions s JOIN security.admin_users a ON a.admin_id = s.admin_id ORDER BY expires_at DESC LIMIT 5")
rows = cur.fetchall()
print("\nRecent sessions:")
for r in rows:
    print(f"  {r['username']} | active={r['is_active']} | expires={r['expires_at']}")

cur.close()
conn.close()
