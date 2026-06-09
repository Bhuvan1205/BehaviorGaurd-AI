import sqlparse

sql = """
CREATE TABLE users (id SERIAL PRIMARY KEY, name VARCHAR DEFAULT 'a;b');

CREATE OR REPLACE FUNCTION test() RETURNS VOID AS $$
BEGIN
    DELETE FROM table WHERE x = y;
    UPDATE table SET x = z;
END;
$$ LANGUAGE plpgsql;

SELECT 1;
"""

# Try splitting
try:
    statements = sqlparse.split(sql)
    for s in statements:
        print("STATEMENT:", s.strip())
except Exception as e:
    print("Error:", e)
