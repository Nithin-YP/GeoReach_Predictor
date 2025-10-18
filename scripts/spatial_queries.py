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

def run_query(conn, query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params or ())
        if cur.description:
            return cur.fetchall()
        else:
            conn.commit()
            return None

def main():
    with psycopg2.connect(**conn_params()) as conn:
        print("=== SPATIAL QUERIES DEMO ===\n")

        # 1. List states with their centroids
        print("1. State centroids:")
        results = run_query(conn, """
            SELECT state_name, ST_AsText(ST_Centroid(geom)) as centroid
            FROM states
            ORDER BY state_name
            LIMIT 5;
        """)
        for row in results:
            print(f"  {row[0]}: {row[1]}")
        print()

        # 2. Calculate area of states
        print("2. State areas (km²):")
        results = run_query(conn, """
            SELECT state_name, ROUND((ST_Area(geom::geography)/1000000)::numeric, 2) as area_km2
            FROM states
            ORDER BY area_km2 DESC
            LIMIT 5;
        """)
        for row in results:
            print(f"  {row[0]}: {row[1]} km²")
        print()

        # 3. Districts within a state (spatial containment)
        print("3. Districts in Maharashtra:")
        results = run_query(conn, """
            SELECT d.district_name
            FROM districts d
            JOIN states s ON d.state_id = s.state_id
            WHERE s.state_name = 'Maharashtra'
            ORDER BY d.district_name
            LIMIT 10;
        """)
        for row in results:
            print(f"  {row[0]}")
        print()

        # 4. Districts intersecting a point (e.g., Mumbai area)
        print("4. Districts containing a point near Mumbai (72.8777, 19.0760):")
        results = run_query(conn, """
            SELECT d.district_name, s.state_name
            FROM districts d
            JOIN states s ON d.state_id = s.state_id
            WHERE ST_Contains(d.geom, ST_SetSRID(ST_Point(72.8777, 19.0760), 4326));
        """)
        for row in results:
            print(f"  {row[0]}, {row[1]}")
        print()

        # 5. Buffer around a point and intersecting districts
        print("5. Districts within 50km of Delhi (77.1025, 28.7041):")
        results = run_query(conn, """
            SELECT d.district_name, s.state_name,
                   ROUND((ST_Distance(d.geom::geography, ST_SetSRID(ST_Point(77.1025, 28.7041), 4326)::geography)/1000)::numeric, 2) as distance_km
            FROM districts d
            JOIN states s ON d.state_id = s.state_id
            WHERE ST_DWithin(d.geom::geography, ST_SetSRID(ST_Point(77.1025, 28.7041), 4326)::geography, 50000)
            ORDER BY distance_km
            LIMIT 5;
        """)
        for row in results:
            print(f"  {row[0]}, {row[1]}: {row[2]} km")
        print()

        # 6. Spatial join: Expenditures in districts of a state
        print("6. Average income in Maharashtra districts:")
        results = run_query(conn, """
            SELECT d.district_name, ROUND(AVG(e.income)::numeric, 2) as avg_income
            FROM expenditures e
            JOIN districts d ON e.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            WHERE s.state_name = 'Maharashtra'
            GROUP BY d.district_name
            ORDER BY avg_income DESC
            LIMIT 5;
        """)
        for row in results:
            print(f"  {row[0]}: ₹{row[1]}")
        print()

        # 7. Employment statistics by state
        print("7. Employment status distribution in Karnataka:")
        results = run_query(conn, """
            SELECT employment_status, COUNT(*) as count
            FROM employment e
            JOIN states s ON e.state_id = s.state_id
            WHERE s.state_name = 'Karnataka'
            GROUP BY employment_status
            ORDER BY count DESC;
        """)
        for row in results:
            print(f"  {row[0]}: {row[1]}")
        print()

        # 7b. District-level employment in Maharashtra
        print("7b. Employment by district in Maharashtra:")
        results = run_query(conn, """
            SELECT d.district_name, e.employment_status, COUNT(*) as count
            FROM employment e
            JOIN districts d ON e.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            WHERE s.state_name = 'Maharashtra'
            GROUP BY d.district_name, e.employment_status
            ORDER BY d.district_name, count DESC
            LIMIT 10;
        """)
        for row in results:
            print(f"  {row[0]} - {row[1]}: {row[2]}")
        print()

        # 8. Customer spending in urban vs rural (based on location in employment, but approximate)
        print("8. Average customer spending by location type:")
        results = run_query(conn, """
            SELECT e.location, ROUND(AVG(c.spending)::numeric, 2) as avg_spending
            FROM customers c
            JOIN employment e ON c.state_id = e.state_id AND c.district_id = e.district_id
            GROUP BY e.location
            ORDER BY avg_spending DESC;
        """)
        for row in results:
            print(f"  {row[0]}: ₹{row[1]}")
        print()

        # 9. Districts with highest literacy
        print("9. Top 5 districts by literacy rate:")
        results = run_query(conn, """
            SELECT d.district_name, s.state_name, d.literacy_rate
            FROM districts d
            JOIN states s ON d.state_id = s.state_id
            ORDER BY d.literacy_rate DESC
            LIMIT 5;
        """)
        for row in results:
            print(f"  {row[0]}, {row[1]}: {row[2]}%")
        print()

        # 10. Population density analysis
        print("10. States with highest population density:")
        results = run_query(conn, """
            SELECT state_name, population_density
            FROM states
            ORDER BY population_density DESC
            LIMIT 5;
        """)
        for row in results:
            print(f"  {row[0]}: {row[1]} per km²")
        print()

        print("=== SPATIAL QUERIES COMPLETE ===")

if __name__ == "__main__":
    main()