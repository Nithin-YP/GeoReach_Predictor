import os
import psycopg2

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

def main():
    with psycopg2.connect(**conn_params()) as conn:
        cur = conn.cursor()
        tables = ["expenditures", "employment", "customers"]
        for table in tables:
            cur.execute(f"TRUNCATE TABLE {table}")
            print(f"Truncated {table}")
        conn.commit()

if __name__ == "__main__":
    main()