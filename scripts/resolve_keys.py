import os
import psycopg2
from psycopg2 import sql

# Load .env if present
try:
    from dotenv import load_dotenv
    env_paths = [os.path.join(os.path.dirname(__file__), '..', '.env'), os.path.join(os.getcwd(), '.env')]
    for p in env_paths:
        p = os.path.abspath(p)
        if os.path.exists(p):
            load_dotenv(p)
            break
except Exception:
    pass

CFG = {
    "pg_host": os.environ.get("PG_HOST", "localhost"),
    "pg_port": int(os.environ.get("PG_PORT", os.environ.get("PGPORT", 5432))),
    "pg_user": os.environ.get("PG_USER", os.environ.get("PGUSER", "postgres")),
    "pg_password": os.environ.get("PG_PASSWORD", os.environ.get("PGPASSWORD", "postgres")),
    "dbname": os.environ.get("PG_DBNAME", os.environ.get("PGDATABASE", "georeach_db")),
}

def conn_params():
    return {
        "host": CFG["pg_host"],
        "port": CFG["pg_port"],
        "user": CFG["pg_user"],
        "password": CFG["pg_password"],
        "dbname": CFG["dbname"],
    }

def resolve_granularity_foreign_keys(table_name):
    """
    After loading data, resolve state_name/district_name to their IDs.
    This enables proper foreign key relationships and aggregation queries.
    (STATE/DISTRICT only - NO CITY)
    """
    with psycopg2.connect(**conn_params()) as conn:
        cur = conn.cursor()
        
        # Debug: check distinct state_name
        cur.execute(f"SELECT DISTINCT state_name FROM {table_name} WHERE state_name IS NOT NULL LIMIT 5")
        sample_states = [row[0] for row in cur.fetchall()]
        print(f"Sample state_names in {table_name}: {sample_states}")
        
        cur.execute("SELECT DISTINCT state_name FROM states WHERE state_name IS NOT NULL LIMIT 5")
        sample_db_states = [row[0] for row in cur.fetchall()]
        print(f"Sample state_names in states: {sample_db_states}")
        
        # Update state_id based on state_name
        print(f"Resolving state_id for {table_name}...")
        cur.execute(f"""
            UPDATE {table_name} t
            SET state_id = s.state_id
            FROM states s
            WHERE t.state_name IS NOT NULL 
            AND t.state_id IS NULL
            AND TRIM(LOWER(t.state_name)) = TRIM(LOWER(s.state_name))
        """)
        print(f"  Updated {cur.rowcount} rows with state_id")
        
        # Update district_id based on district_name and state_id
        print(f"Resolving district_id for {table_name}...")
        cur.execute(f"""
            UPDATE {table_name} t
            SET district_id = d.district_id
            FROM districts d
            WHERE t.district_name IS NOT NULL 
            AND t.district_id IS NULL
            AND t.state_id = d.state_id
            AND TRIM(LOWER(t.district_name)) = TRIM(LOWER(d.district_name))
        """)
        print(f"  Updated {cur.rowcount} rows with district_id")
        
        conn.commit()
        print(f"Foreign key resolution complete for {table_name}")

def main():
    tables = ["expenditures", "employment", "customers"]
    for table in tables:
        resolve_granularity_foreign_keys(table)

if __name__ == "__main__":
    main()