import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def test_query():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433")
    )
    cur = conn.cursor()
    try:
        cur.execute("""
            WITH latest_risk AS (
                SELECT DISTINCT ON (r.user_id)
                    r.user_id,
                    r.risk_score AS latest_risk,
                    r.risk_level AS latest_risk_level,
                    r.window_start AS latest_event_timestamp
                FROM security.risk_scores r
                ORDER BY r.user_id, r.window_start DESC
            ),
            risk_stats AS (
                SELECT
                    r.user_id,
                    AVG(r.risk_score) AS avg_risk,
                    COUNT(*) AS history_count,
                    SUM(CASE WHEN r.anomaly_flag THEN 1 ELSE 0 END) AS anomaly_count
                FROM security.risk_scores r
                GROUP BY r.user_id
            ),
            alert_stats AS (
                SELECT
                    a.user_id,
                    COUNT(*) AS alert_count,
                    SUM(CASE WHEN a.status = 'OPEN' THEN 1 ELSE 0 END) AS open_alert_count
                FROM security.alerts a
                GROUP BY a.user_id
            )
            SELECT
                u.user_id
            FROM core.users u
            LEFT JOIN latest_risk lr ON lr.user_id = u.user_id
            LEFT JOIN risk_stats rs ON rs.user_id = u.user_id
            LEFT JOIN alert_stats al ON al.user_id = u.user_id
            WHERE u.status = 'active'
        """)
        print("Success:", cur.fetchall())
    except Exception as e:
        print("Error:", e)
    cur.close()
    conn.close()

if __name__ == "__main__":
    test_query()
