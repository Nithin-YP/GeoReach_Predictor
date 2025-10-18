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

def table_exists(conn, table_name):
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)", (table_name.split('.')[-1],))
        return cur.fetchone()[0]

def update_districts_geom_from_imported(table_geom):
    """Update districts.geom from an imported shapefile table. Attempts to detect the name column and match to districts.district_name."""
    with psycopg2.connect(**conn_params()) as conn:
        if not table_exists(conn, f"public.{table_geom}"):
            print(f"Table public.{table_geom} does not exist; skipping districts geom update.")
            return
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
                (table_geom,)
            )
            cols = [r[0] for r in cur.fetchall()]
        norm = {c.lower(): c for c in cols}
        # candidate names for district label fields
        if 'districts' in table_geom.lower():
            candidates = ['name_2', 'district', 'district_name', 'name', 'NAME_1', 'NAME', 'DISTRICT', 'dist_name', 'districtna']
        else:
            candidates = ['district', 'district_name', 'name', 'NAME_1', 'NAME', 'DISTRICT', 'dist_name', 'districtna']
        chosen = None
        for cand in candidates:
            if cand.lower() in norm:
                chosen = norm[cand.lower()]
                break
        if not chosen:
            print(f"Could not find a district name column in public.{table_geom}. Columns: {cols}")
            return
        # perform update: match districts.district_name to geometry table's chosen column
        update_sql = sql.SQL(
            "UPDATE districts d SET geom = g.geom FROM public.{geom_table} g WHERE TRIM(LOWER(d.district_name)) = TRIM(LOWER(g.{name_col}));"
        ).format(geom_table=sql.Identifier(table_geom), name_col=sql.Identifier(chosen))
        with conn.cursor() as cur:
            cur.execute(update_sql)
            print(f"Updated {cur.rowcount} districts with geom")
        conn.commit()
        print(f"Updated districts.geom from public.{table_geom}")

def main():
    update_districts_geom_from_imported("districts_geom")

if __name__ == "__main__":
    main()