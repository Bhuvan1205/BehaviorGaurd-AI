import os
import json
import glob
import uuid
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd

DB_CONFIG = {
    "dbname": "behavior_guard_ai",
    "user": "postgres",
    "password": "Bhuvan2005!",
    "host": "localhost",
    "port": "5433"
}

def create_database_if_not_exists():
    """Connect to default database 'postgres' and ensure 'behavior_guard_ai' is created fresh."""
    print("Connecting to postgres default database to check/create behavior_guard_ai...")
    conn = psycopg2.connect(
        dbname="postgres",
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"]
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # Check if database exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'behavior_guard_ai';")
    exists = cur.fetchone()
    
    if exists:
        print("Database 'behavior_guard_ai' already exists. Dropping it for a clean setup...")
        cur.execute("""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = 'behavior_guard_ai'
              AND pid <> pg_backend_pid();
        """)
        cur.execute("DROP DATABASE behavior_guard_ai;")
        print("Database dropped.")
        
    print("Creating database 'behavior_guard_ai'...")
    cur.execute("CREATE DATABASE behavior_guard_ai;")
    print("Database 'behavior_guard_ai' created successfully!")
        
    cur.close()
    conn.close()

def run_migrations():
    """Run all schema scripts Database/DB M*.sql on port 5433."""
    print("\nRunning database schema migrations...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    sql_files = sorted(glob.glob("Database/DB M*.sql"))
    print(f"Found SQL files: {sql_files}")

    for file_path in sql_files:
        print(f"Executing {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()
            # Ignore CREATE DATABASE since we handle it
            sql = sql.replace("CREATE DATABASE behavior_guard_ai;", "-- CREATE DATABASE behavior_guard_ai;")
            # Drop existing roles before creating to avoid DuplicateObject errors (roles are global in PG)
            sql = sql.replace("CREATE ROLE backend_service", "DROP ROLE IF EXISTS backend_service; CREATE ROLE backend_service")
            sql = sql.replace("CREATE ROLE ml_service", "DROP ROLE IF EXISTS ml_service; CREATE ROLE ml_service")
            sql = sql.replace("CREATE ROLE read_only_analyst", "DROP ROLE IF EXISTS read_only_analyst; CREATE ROLE read_only_analyst")
        try:
            cur.execute(sql)
            print(f"Successfully executed {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error executing {os.path.basename(file_path)}:")
            print(e)
            raise e

    cur.close()
    conn.close()

def seed_users():
    """Seed core.departments, core.roles, and core.users from data/raw/users.csv."""
    print("\nSeeding core.departments, core.roles, and core.users from raw users.csv...")
    users_csv_path = "data/raw/users.csv"
    if not os.path.exists(users_csv_path):
        raise FileNotFoundError(f"Raw users CSV not found at {users_csv_path}")

    # Load users
    df = pd.read_csv(users_csv_path)
    print(f"Loaded {len(df)} users from CSV.")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Seed Departments
        departments = df["department"].dropna().unique()
        print(f"Seeding {len(departments)} departments...")
        dept_mapping = {}
        for dept in departments:
            dept_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO core.departments (department_id, department_name)
                VALUES (%s, %s)
                ON CONFLICT (department_name) DO UPDATE
                SET department_name = EXCLUDED.department_name
                RETURNING department_id;
            """, (dept_id, dept))
            # Get the actual database UUID (whether new or existing)
            actual_id = cur.fetchone()[0]
            dept_mapping[dept] = actual_id

        # 2. Seed Roles
        roles = df["role"].dropna().unique()
        print(f"Seeding {len(roles)} roles...")
        role_mapping = {}
        for role in roles:
            role_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO core.roles (role_id, role_name)
                VALUES (%s, %s)
                ON CONFLICT (role_name) DO UPDATE
                SET role_name = EXCLUDED.role_name
                RETURNING role_id;
            """, (role_id, role))
            actual_id = cur.fetchone()[0]
            role_mapping[role] = actual_id

        # 3. Seed Users
        print("Seeding core.users...")
        user_uuid_mapping = {}
        users_to_insert = []
        
        for _, row in df.iterrows():
            emp_id = row["user_id"]
            full_name = row["employee_name"]
            email = row["email"]
            role_name = row["role"]
            dept_name = row["department"]
            
            hire_date = pd.to_datetime(row["start_date"], errors="coerce")
            hire_date_val = hire_date.date() if not pd.isna(hire_date) else None
            
            # Map foreign keys
            dept_uuid = dept_mapping.get(dept_name)
            role_uuid = role_mapping.get(role_name)
            
            user_uuid = str(uuid.uuid4())
            
            users_to_insert.append((
                user_uuid,
                emp_id,
                full_name,
                email,
                dept_uuid,
                role_uuid,
                hire_date_val,
                "active"
            ))

        execute_values(
            cur,
            """
            INSERT INTO core.users (
                user_id, employee_id, full_name, email, department_id, role_id, hire_date, status
            )
            VALUES %s
            ON CONFLICT (employee_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                email = EXCLUDED.email,
                department_id = EXCLUDED.department_id,
                role_id = EXCLUDED.role_id,
                hire_date = EXCLUDED.hire_date,
                status = EXCLUDED.status
            """,
            users_to_insert
        )
        
        # Load user UUIDs back from database to ensure we have the exact mapped UUIDs
        cur.execute("SELECT employee_id, user_id::text FROM core.users;")
        for emp, db_uuid in cur.fetchall():
            user_uuid_mapping[emp] = db_uuid

        conn.commit()
        print("Base seeding completed successfully!")
        return user_uuid_mapping
        
    except Exception as e:
        conn.rollback()
        print("Error during base seeding:")
        print(e)
        raise e
    finally:
        cur.close()
        conn.close()

def create_new_tables():
    """Create the two new tables core.user_clusters and ml.cluster_model_registry."""
    print("\nCreating new tables core.user_clusters and ml.cluster_model_registry...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Table 1: core.user_clusters
        print("Creating Table 1: core.user_clusters...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS core.user_clusters (
                cluster_record_id  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                user_id            UUID NOT NULL REFERENCES core.users(user_id),
                shift              VARCHAR(10) NOT NULL CHECK (shift IN ('Day', 'Evening', 'Night')),
                role_group         VARCHAR(50) NOT NULL,
                cluster_id         INTEGER NOT NULL CHECK (cluster_id IN (0, 1, 2, 3)),
                assigned_at        TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (user_id, shift)
            );
        """)
        
        # Index for Table 1
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_clusters_lookup 
            ON core.user_clusters (user_id, shift);
        """)
        print("Table 1 core.user_clusters created successfully.")

        # Table 2: ml.cluster_model_registry
        print("Creating Table 2: ml.cluster_model_registry...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ml.cluster_model_registry (
                registry_id        UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                shift              VARCHAR(10) NOT NULL CHECK (shift IN ('Day', 'Evening', 'Night')),
                role_group         VARCHAR(50) NOT NULL,
                cluster_id         INTEGER NOT NULL CHECK (cluster_id IN (0, 1, 2, 3)),
                model_path         TEXT NOT NULL,
                threshold_value    DOUBLE PRECISION NOT NULL,
                created_at         TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (shift, role_group, cluster_id)
            );
        """)

        # Index for Table 2
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_cluster_model_lookup 
            ON ml.cluster_model_registry (shift, role_group, cluster_id);
        """)
        print("Table 2 ml.cluster_model_registry created successfully.")

    except Exception as e:
        print("Error creating new tables:")
        print(e)
        raise e
    finally:
        cur.close()
        conn.close()

def populate_new_tables(user_uuid_mapping):
    """Populate core.user_clusters and ml.cluster_model_registry."""
    print("\nPopulating new tables...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Populate core.user_clusters from user_cluster_assignments.csv
        assignments_path = "notebooks/models/cluster_models/user_cluster_assignments.csv"
        print(f"Loading assignments from {assignments_path}...")
        df_assign = pd.read_csv(assignments_path)
        
        cluster_rows = []
        missing_users = 0
        
        for _, row in df_assign.iterrows():
            emp_id = row["user_id"]
            shift = row["shift"]
            role_group = row["role_group"]
            cluster_id = int(row["cluster_id"])
            assigned_at = row["assigned_at"]
            
            user_uuid = user_uuid_mapping.get(emp_id)
            if not user_uuid:
                missing_users += 1
                continue
                
            cluster_rows.append((
                user_uuid,
                shift,
                role_group,
                cluster_id,
                assigned_at
            ))
            
        if missing_users > 0:
            print(f"Warning: {missing_users} users in assignments CSV were not found in core.users!")

        print(f"Inserting {len(cluster_rows)} assignments into core.user_clusters...")
        execute_values(
            cur,
            """
            INSERT INTO core.user_clusters (user_id, shift, role_group, cluster_id, assigned_at)
            VALUES %s
            ON CONFLICT (user_id, shift) DO UPDATE SET
                role_group = EXCLUDED.role_group,
                cluster_id = EXCLUDED.cluster_id,
                assigned_at = EXCLUDED.assigned_at
            """,
            cluster_rows
        )

        # 2. Populate ml.cluster_model_registry from cluster_thresholds.json
        thresholds_path = "notebooks/models/cluster_models/cluster_thresholds.json"
        print(f"Loading thresholds from {thresholds_path}...")
        with open(thresholds_path, "r") as f:
            thresholds = json.load(f)
            
        registry_rows = []
        for key, threshold in thresholds.items():
            # Key format: {shift}_{role_group}_{cluster_id} (e.g. Day_engineering_0)
            parts = key.split("_")
            shift = parts[0]
            role_group = "_".join(parts[1:-1])
            cluster_id = int(parts[-1])
            
            # Lowercase shift for filename per feedback
            shift_lower = shift.lower()
            model_path = f"notebooks/models/cluster_models/{shift_lower}_{role_group}_{cluster_id}_if.pkl"
            
            registry_rows.append((
                shift,
                role_group,
                cluster_id,
                model_path,
                threshold
            ))
            
        print(f"Inserting {len(registry_rows)} thresholds into ml.cluster_model_registry...")
        execute_values(
            cur,
            """
            INSERT INTO ml.cluster_model_registry (shift, role_group, cluster_id, model_path, threshold_value)
            VALUES %s
            ON CONFLICT (shift, role_group, cluster_id) DO UPDATE SET
                model_path = EXCLUDED.model_path,
                threshold_value = EXCLUDED.threshold_value
            """,
            registry_rows
        )

        conn.commit()
        print("Data population completed successfully!")

    except Exception as e:
        conn.rollback()
        print("Error during data population:")
        print(e)
        raise e
    finally:
        cur.close()
        conn.close()

def verify_counts():
    """Verify and print counts for the new tables."""
    print("\nVerifying database row counts...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM core.user_clusters;")
        uc_count = cur.fetchone()[0]
        print(f"Row count in core.user_clusters: {uc_count} (Expected: 12000)")

        cur.execute("SELECT COUNT(*) FROM ml.cluster_model_registry;")
        registry_count = cur.fetchone()[0]
        print(f"Row count in ml.cluster_model_registry: {registry_count} (Expected: 112)")

        # Query a sample from core.user_clusters
        cur.execute("""
            SELECT u.employee_id, uc.shift, uc.role_group, uc.cluster_id, uc.assigned_at
            FROM core.user_clusters uc
            JOIN core.users u ON uc.user_id = u.user_id
            LIMIT 3;
        """)
        print("\nSample records from core.user_clusters:")
        for row in cur.fetchall():
            print(f"  Employee: {row[0]}, Shift: {row[1]}, Role Group: {row[2]}, Cluster: {row[3]}, Assigned At: {row[4]}")

        # Query a sample from ml.cluster_model_registry
        cur.execute("""
            SELECT shift, role_group, cluster_id, model_path, threshold_value
            FROM ml.cluster_model_registry
            LIMIT 3;
        """)
        print("\nSample records from ml.cluster_model_registry:")
        for row in cur.fetchall():
            print(f"  Shift: {row[0]}, Role Group: {row[1]}, Cluster: {row[2]}, Path: {row[3]}, Threshold: {row[4]}")

    except Exception as e:
        print("Error during validation queries:")
        print(e)
    finally:
        cur.close()
        conn.close()

def main():
    create_database_if_not_exists()
    run_migrations()
    user_uuid_mapping = seed_users()
    create_new_tables()
    populate_new_tables(user_uuid_mapping)
    verify_counts()

if __name__ == "__main__":
    main()
