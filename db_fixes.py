import psycopg2


def main():
    conn = psycopg2.connect(
        dbname="behavior_guard_ai",
        user="postgres",
        password="Bhuvan2005!",
        host="localhost",
        port="5432",
    )
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("Adding unique constraint for feature windows if needed...")
        try:
            cur.execute(
                """
                ALTER TABLE features.user_behavior_features
                ADD CONSTRAINT unique_user_window UNIQUE (user_id, window_start)
                """
            )
            print("Added unique_user_window.")
        except psycopg2.errors.DuplicateObject:
            conn.rollback()
            print("unique_user_window already exists.")

        print("Creating March 2026 partitions if needed...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS features.user_behavior_features_2026_03
            PARTITION OF features.user_behavior_features
            FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

            CREATE TABLE IF NOT EXISTS security.risk_scores_2026_03
            PARTITION OF security.risk_scores_new
            FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
            """
        )
        print("March 2026 partitions are ready.")

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
