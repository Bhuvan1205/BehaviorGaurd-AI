import psycopg2
import glob
import os
import sqlparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _tables_ready(cur):
    """Return True if all required flat tables exist with the correct schema."""
    required = [
        ("core",     "users"),
        ("security", "risk_scores"),
        ("security", "alerts"),
        ("security", "admin_users"),
        ("features", "user_behavior_features"),
        ("events",   "email_events"),
    ]
    for schema, table in required:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (schema, table),
        )
        if not cur.fetchone():
            print(f"  Missing table: {schema}.{table}")
            return False

    # Also confirm risk_scores is NOT partitioned (flat check)
    cur.execute(
        "SELECT c.relkind FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'security' AND c.relname = 'risk_scores'",
    )
    row = cur.fetchone()
    if row and row[0] == 'p':
        print("  security.risk_scores is still partitioned — migration needed.")
        return False

    return True


def setup_db():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "behavior_guard_ai"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "Bhuvan2005!"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433")
    )
    conn.autocommit = True
    cur = conn.cursor()

    # ── Fast-path: skip all migrations if the schema is already correct ──────
    print("Checking database schema state...")
    try:
        if _tables_ready(cur):
            print("All required tables exist with correct schema. Skipping migrations.")
            cur.close()
            conn.close()
            return
        else:
            print("Schema incomplete or outdated — running full migrations.")
    except Exception as e:
        print(f"Schema check warning (will run full migrations): {e}")

    # Pre-migration cleanup: check if we need to migrate from partitioned to flat tables
    try:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'security' AND table_name = 'risk_scores_old'
            ) OR EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'features' AND c.relname = 'user_behavior_features' AND c.relkind = 'p'
            );
            """
        )
        needs_flattening = cur.fetchone()[0]
        if needs_flattening:
            print("Detected legacy partitioned tables or risk_scores_old. Performing one-time flattening drop...")
            cur.execute("DROP TABLE IF EXISTS security.alerts CASCADE;")
            cur.execute("DROP TABLE IF EXISTS security.risk_scores CASCADE;")
            cur.execute("DROP TABLE IF EXISTS security.risk_scores_old CASCADE;")
            cur.execute("DROP TABLE IF EXISTS security.risk_scores_new CASCADE;")
            cur.execute("DROP TABLE IF EXISTS features.user_behavior_features CASCADE;")
            print("One-time flattening drop complete.")
    except Exception as e:
        print("Pre-migration cleanup warning:", e)

    sql_files = sorted(glob.glob("Database/DB M*.sql"))
    print(f"Found SQL files: {sql_files}")

    db_name = os.getenv("DB_NAME", "behavior_guard_ai")

    for file_path in sql_files:
        print(f"Executing {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            sql = f.read()
            # Ignore CREATE DATABASE
            sql = sql.replace("CREATE DATABASE behavior_guard_ai;", "-- CREATE DATABASE behavior_guard_ai;")

        # Custom state machine to split statements, avoiding sqlparse which might hang on some environments
        statements = []
        current_stmt = []
        in_single_quote = False
        in_dollar_quote = False
        dollar_tag = ""
        
        i = 0
        length = len(sql)
        while i < length:
            char = sql[i]
            
            if char == "'" and not in_dollar_quote:
                in_single_quote = not in_single_quote
                current_stmt.append(char)
                i += 1
                continue
                
            if char == '$' and not in_single_quote:
                tag_end = sql.find('$', i + 1)
                if tag_end != -1:
                    potential_tag = sql[i:tag_end+1]
                    if not in_dollar_quote:
                        in_dollar_quote = True
                        dollar_tag = potential_tag
                    elif in_dollar_quote and potential_tag == dollar_tag:
                        in_dollar_quote = False
                        dollar_tag = ""
                    current_stmt.append(potential_tag)
                    i = tag_end + 1
                    continue
                    
            if char == ';' and not in_single_quote and not in_dollar_quote:
                statements.append("".join(current_stmt).strip())
                current_stmt = []
                i += 1
                continue
                
            current_stmt.append(char)
            i += 1
            
        if "".join(current_stmt).strip():
            statements.append("".join(current_stmt).strip())

        success_count = 0
        ignored_count = 0

        for stmt_clean in statements:
            if not stmt_clean:
                continue

            # Replace database name reference in SQL statements (like GRANT CONNECT ON DATABASE)
            stmt_clean = stmt_clean.replace("behavior_guard_ai", db_name)

            print(f"Executing statement: {stmt_clean[:100]}...")

            try:
                cur.execute(stmt_clean)
                success_count += 1
            except Exception as e:
                err_msg = str(e).lower()
                # Ignore expected warnings when running on cloud databases (e.g. Supabase, Neon)
                if any(x in err_msg for x in ["already exists", "permission denied", "must be superuser", "role", "grant", "connect", "empty query", "does not exist", "multiple primary keys", "not partitioned"]):
                    ignored_count += 1
                else:
                    print(f"Critical error on statement: {stmt_clean[:150]}...")
                    print(e)
                    raise e

        print(f"Finished executing {os.path.basename(file_path)}: {success_count} statements succeeded, {ignored_count} non-critical warnings ignored.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    setup_db()
