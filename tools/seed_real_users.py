#!/usr/bin/env python3
import os
import sys
import json
import uuid
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
from dotenv import load_dotenv

# Ensure we can run this from the project root or tools directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env variables from .env
load_dotenv()

def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433")
    )

def seed_users():
    print("\nSeeding core.departments, core.roles, and core.users from raw users.csv...")
    users_csv_path = "data/raw/users.csv"
    if not os.path.exists(users_csv_path):
        raise FileNotFoundError(f"Raw users CSV not found at {users_csv_path}")

    # Load users
    df = pd.read_csv(users_csv_path)
    print(f"Loaded {len(df)} users from CSV.")

    conn = get_connection()
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
        
        # Load user UUIDs back from database
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
    print("\nCreating new tables core.user_clusters and ml.cluster_model_registry...")
    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # Table 1: core.user_clusters
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
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_clusters_lookup 
            ON core.user_clusters (user_id, shift);
        """)
        print("Table 1 core.user_clusters created successfully.")

        # Table 2: ml.cluster_model_registry
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
    print("\nPopulating new tables...")
    conn = get_connection()
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
            parts = key.split("_")
            shift = parts[0]
            role_group = "_".join(parts[1:-1])
            cluster_id = int(parts[-1])
            
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
    print("\nVerifying database row counts...")
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM core.users;")
        u_count = cur.fetchone()[0]
        print(f"Row count in core.users: {u_count} (Expected: 4000)")

        cur.execute("SELECT COUNT(*) FROM core.departments;")
        dept_count = cur.fetchone()[0]
        print(f"Row count in core.departments: {dept_count} (Expected: 30)")

        cur.execute("SELECT COUNT(*) FROM core.user_clusters;")
        uc_count = cur.fetchone()[0]
        print(f"Row count in core.user_clusters: {uc_count} (Expected: 12000)")

        cur.execute("SELECT COUNT(*) FROM ml.cluster_model_registry;")
        registry_count = cur.fetchone()[0]
        print(f"Row count in ml.cluster_model_registry: {registry_count} (Expected: 112)")

    except Exception as e:
        print("Error during validation queries:", e)
    finally:
        cur.close()
        conn.close()

def main():
    user_uuid_mapping = seed_users()
    create_new_tables()
    populate_new_tables(user_uuid_mapping)
    verify_counts()

if __name__ == "__main__":
    main()
