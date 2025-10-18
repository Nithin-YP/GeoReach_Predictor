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
        
        # Get columns for states_geom
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'states_geom' ORDER BY ordinal_position")
        cols = [row[0] for row in cur.fetchall()]
        print(f"States_geom columns: {cols}")
        
        # Get columns for districts_geom
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'districts_geom' ORDER BY ordinal_position")
        cols = [row[0] for row in cur.fetchall()]
        print(f"Districts_geom columns: {cols}")
        
        # Assume name columns
        # For states: name_1
        # For districts: name_2 for district, name_1 for state
        
        # Get state names
        cur.execute("SELECT DISTINCT name_1 FROM states_geom ORDER BY name_1")
        states = [row[0] for row in cur.fetchall()]
        print(f"States: {len(states)}")
        print(states[:5])
        
        # Get district names
        cur.execute("SELECT DISTINCT name_2, name_1 FROM districts_geom ORDER BY name_1, name_2")
        districts = cur.fetchall()
        print(f"Districts: {len(districts)}")
        print(districts[:5])
        
        # Save to files
        with open("states_from_shp.txt", "w") as f:
            for s in states:
                f.write(s + "\n")
        
        with open("districts_from_shp.txt", "w") as f:
            for d, s in districts:
                f.write(f"{d},{s}\n")

if __name__ == "__main__":
    main()