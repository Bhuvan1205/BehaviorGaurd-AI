#!/bin/sh
set -e

echo "Waiting for PostgreSQL to start..."
python -c "
import os, sys, time, psycopg2
dbname = os.getenv('DB_NAME', 'behavior_guard_ai')
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD', 'Bhuvan2005!')
host = os.getenv('DB_HOST', 'localhost')
port = os.getenv('DB_PORT', '5433')
attempts = 0
while attempts < 30:
    try:
        conn = psycopg2.connect(dbname=dbname, user=user, password=password, host=host, port=port)
        conn.close()
        print('PostgreSQL is up and running!')
        sys.exit(0)
    except psycopg2.OperationalError as e:
        print(f'Attempt {attempts+1}/30: PostgreSQL not ready yet ({e.args[0].strip() if e.args else e})')
        time.sleep(1.5)
        attempts += 1
print('PostgreSQL did not become ready in time. Exiting.')
sys.exit(1)
"

echo "Starting Uvicorn backend server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

echo "Running database schema migrations in background..."
python setup_db.py &

if [ "$SEED_DEMO_DATA" = "true" ]; then
  echo "Seeding database with initial demo data (background)..."
  python seed_demo_data.py &
fi

# Keep uvicorn as the main process
wait $UVICORN_PID
