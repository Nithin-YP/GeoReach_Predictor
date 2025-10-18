import os
import subprocess
import csv
import re
import psycopg2
from psycopg2 import sql

# load .env if present
try:
    from dotenv import load_dotenv
    # prefer a .env in the project root (two levels up from scripts/) then current dir
    env_paths = [os.path.join(os.path.dirname(__file__), '..', '.env'), os.path.join(os.getcwd(), '.env')]
    for p in env_paths:
        p = os.path.abspath(p)
        if os.path.exists(p):
            load_dotenv(p)
            print(f"Loaded environment from {p}")
            break
    else:
        # try default load (will read .env in cwd if present)
        load_dotenv()
except Exception:
    # dotenv not installed or failed to load; proceed with environment variables only
    pass

# Simple configurable settings (edit before running)
def _env_bool(key, default=False):
    v = os.environ.get(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y", "on")

CFG = {
    "pg_host": os.environ.get("PG_HOST", "localhost"),
    "pg_port": int(os.environ.get("PG_PORT", os.environ.get("PGPORT", 5432))),
    "pg_user": os.environ.get("PG_USER", os.environ.get("PGUSER", "georeach")),
    "pg_password": os.environ.get("PG_PASSWORD", os.environ.get("PGPASSWORD", "pass")),
    "create_db": _env_bool("CREATE_DB", True),
    "dbname": os.environ.get("PG_DBNAME", os.environ.get("PGDATABASE", "georeach_db")),
    "pg_bin": os.environ.get("PG_BIN", r"C:\\Program Files\\PostgreSQL\\17\\bin"),
    # CSV files (example relative paths on Windows) - these can be overridden in .env
    "csv_states_1": os.environ.get("CSV_STATES_1", r"..\\datasets\\geodata\\dataset1.csv"),
    "csv_states_4": os.environ.get("CSV_STATES_4", r"..\\datasets\\geodata\\dataset4.csv"),
    "csv_districts": os.environ.get("CSV_DISTRICTS", r"..\\datasets\\geodata\\dataset2.csv"),
    "csv_expenditures": os.environ.get("CSV_EXPENDITURES", r"..\\datasets\\geodata\\dataset3.csv"),
    "csv_employment": os.environ.get("CSV_EMPLOYMENT", r"..\\datasets\\geodata\\dataset5.csv"),
    "csv_customers": os.environ.get("CSV_CUSTOMERS", r"..\\datasets\\geodata\\dataset6.csv"),
    # shapefile path (optional)
    "shp_states": os.environ.get("SHP_STATES", r"..\\datasets\\geodata\\india_states.shp"),
    "shp_districts": os.environ.get("SHP_DISTRICTS", r"..\\datasets\\geodata\\india_districts.shp"),
}

def conn_params(dbname="postgres"):
    return {
        "host": CFG["pg_host"],
        "port": CFG["pg_port"],
        "user": CFG["pg_user"],
        "password": CFG["pg_password"],
        "dbname": dbname,
    }


def auto_detect_pg_bin():
    """Try to find PostgreSQL bin directory (where psql.exe and shp2pgsql.exe live).
    Preference order: CFG['pg_bin'] if valid, common Program Files locations, PATH.
    """
    # if user provided and valid
    user = CFG.get('pg_bin')
    if user and os.path.exists(os.path.join(user, 'psql.exe')):
        print(f"Using pg_bin from CFG: {user}")
        return user

    # check common versions under Program Files
    pf = os.environ.get('ProgramFiles', r'C:\Program Files')
    candidates = []
    for v in ('17', '16', '15', '14'):
        candidates.append(os.path.join(pf, f'PostgreSQL\{v}\bin'))
        candidates.append(os.path.join(pf, f'PostgreSQL\{v}'))
    # also check pgAdmin runtime
    candidates.append(os.path.join(pf, 'PostgreSQL'))

    for c in candidates:
        if os.path.exists(os.path.join(c, 'psql.exe')):
            print(f"Found psql in: {c}")
            return c

    # fallback: check PATH for psql.exe
    for path_dir in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(path_dir, 'psql.exe')
        if os.path.exists(p):
            print(f"Found psql on PATH in: {path_dir}")
            return path_dir

    print("psql/shp2pgsql not found automatically. Please set CFG['pg_bin'] to your PostgreSQL bin directory.")
    return CFG.get('pg_bin')

def run_sql(conn, sql_text, params=None):
    with conn.cursor() as cur:
        cur.execute(sql_text, params or ())
    conn.commit()

def create_database_if_missing():
    params = conn_params(dbname="postgres")
    # use a connection with AUTOCOMMIT/isolation level AUTOCOMMIT so CREATE DATABASE is not inside a transaction
    conn = psycopg2.connect(**params)
    try:
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (CFG["dbname"],))
            if cur.fetchone():
                print(f"Database '{CFG['dbname']}' already exists.")
            else:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(CFG["dbname"])))
                print(f"Created database '{CFG['dbname']}'.")
    finally:
        conn.close()

def enable_postgis_extensions():
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        conn.autocommit = True
        print("Enabling PostGIS extensions...")
        run_sql(conn, "CREATE EXTENSION IF NOT EXISTS postgis;")
        run_sql(conn, "CREATE EXTENSION IF NOT EXISTS postgis_topology;")
        print("PostGIS extensions enabled.")

def create_core_tables():
    ddl = """
    CREATE TABLE IF NOT EXISTS states (
        state_id SERIAL PRIMARY KEY,
        state_name VARCHAR(100) UNIQUE,
        population BIGINT,
        population_percent NUMERIC,
        male BIGINT,
        female BIGINT,
        rural BIGINT,
        urban BIGINT,
        area_km2 NUMERIC,
        population_density NUMERIC,
        est_unemployment_rate NUMERIC,
        est_employed BIGINT,
        area_type VARCHAR(50),
        geom GEOMETRY(MULTIPOLYGON, 4326)
    );

    CREATE TABLE IF NOT EXISTS districts (
        district_id SERIAL PRIMARY KEY,
        district_name VARCHAR(100),
        state_id INT,
        population_district BIGINT,
        literacy_rate NUMERIC,
        geom GEOMETRY(MULTIPOLYGON, 4326),
        FOREIGN KEY (state_id) REFERENCES states(state_id)
    );

    CREATE TABLE IF NOT EXISTS expenditures (
        id SERIAL PRIMARY KEY,
        income NUMERIC,
        age INT,
        occupation VARCHAR(100),
        city_tier VARCHAR(20),
        groceries_exp NUMERIC,
        transport_exp NUMERIC,
        eating_out_exp NUMERIC,
        entertainment_exp NUMERIC,
        utilities_exp NUMERIC,
        healthcare_exp NUMERIC,
        education_exp NUMERIC,
        misc_exp NUMERIC,
        disposable_income NUMERIC,
        potential_savings_groceries NUMERIC,
        potential_savings_transport NUMERIC,
        potential_savings_eating_out NUMERIC,
        potential_savings_entertainment NUMERIC,
        potential_savings_utilities NUMERIC,
        potential_savings_healthcare NUMERIC,
        potential_savings_education NUMERIC,
        potential_savings_misc NUMERIC
    );

    CREATE TABLE IF NOT EXISTS employment (
        id SERIAL PRIMARY KEY,
        employment_status VARCHAR(100),
        age_group VARCHAR(50),
        education_level VARCHAR(50),
        industry VARCHAR(100),
        location VARCHAR(100),
        monthly_salary_inr NUMERIC
    );

    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        customer_name VARCHAR(100),
        age INT,
        gender VARCHAR(20),
        education_level VARCHAR(50),
        income NUMERIC,
        purchase_frequency NUMERIC,
        spending NUMERIC,
        location VARCHAR(100)
    );
    """
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        run_sql(conn, ddl)
        print("Core tables created.")

# simple header -> table column map (add entries as needed)
HEADER_MAP = {
    "states": {
        # dataset1 headers (normalized) -> table column
        "state_name": "state_name",
        "state": "state_name",
        "stateid": "state_id",
        "population": "population",
        "population_percent": "population_percent",
        "male": "male",
        "female": "female",
        # alternate headers seen in dataset: 'rural (%)' -> normalized 'rural_51_' etc.
        "rural": "rural",
        "rural_51_": "rural",
        "urban": "urban",
        "urban_51_": "urban",
        "area_km2": "area_km2",
        "population_density_per_km2": "population_density",
        "population_density": "population_density",
        "estimated_unemployment_rate_percent": "est_unemployment_rate",
        "estimated_employed": "est_employed",
        "area_type": "area_type",
    },
    "districts": {
        "district_name": "district_name",
        "district": "district_name",
        "districtid": "district_id",
        # CSV contains state name; map to state_name and resolve to state_id during transform
        "state": "state_name",
        "state_id": "state_id",
        "population": "population_district",
        "population_district": "population_district",
        "literacy": "literacy_rate",
        "literacy_rate_percent": "literacy_rate",
    },
    "expenditures": {
        # map common verbose headers to compact table columns
        "income": "income",
        "age": "age",
        "occupation": "occupation",
        "city_tier": "city_tier",
        "groceries_expenditure": "groceries_exp",
        "groceries": "groceries_exp",
        "transport_expenditure": "transport_exp",
        "transport": "transport_exp",
        "eating_out_expenditure": "eating_out_exp",
        "eating_out": "eating_out_exp",
        "entertainment_expenditure": "entertainment_exp",
        "utilities_expenditure": "utilities_exp",
        "healthcare_expenditure": "healthcare_exp",
        "education_expenditure": "education_exp",
        "miscellaneous_expenditure": "misc_exp",
        "misc": "misc_exp",
        "disposable_income": "disposable_income",
        # optionally map potential savings columns if present
        "potential_savings_groceries": "potential_savings_groceries",
        "potential_savings_transport": "potential_savings_transport",
        "potential_savings_eating_out": "potential_savings_eating_out",
        "potential_savings_entertainment": "potential_savings_entertainment",
        "potential_savings_utilities": "potential_savings_utilities",
        "potential_savings_healthcare": "potential_savings_healthcare",
        "potential_savings_education": "potential_savings_education",
        "potential_savings_miscellaneous": "potential_savings_misc",
    },
    "employment": {
        "employment_status": "employment_status",
        "age_group": "age_group",
        "education_level": "education_level",
        "industry": "industry",
        "location": "location",
        "monthly_salary_inr": "monthly_salary_inr",
    },
    "customers": {
        "customer_name": "customer_name",
        "age": "age",
        "gender": "gender",
        "education_level": "education_level",
        "income": "income",
        "purchase_frequency": "purchase_frequency",
        "spending": "spending",
        "location": "location",
    }
}

def _normalize_header(h):
    h = h.strip().lower()
    h = re.sub(r'[^a-z0-9_]', '_', h)
    h = re.sub(r'__+', '_', h)
    return h

def infer_columns_for_table(table, csv_path):
    """
    Read CSV header and map to known table columns using HEADER_MAP.
    Returns list of column names for COPY in correct order (based on CSV header).
    """
    base = os.path.splitext(os.path.basename(csv_path))[0]
    key = table.lower()
    # prefer explicit map by table name, fallback to generic mapping
    mapping = HEADER_MAP.get(key, {})
    with open(csv_path, "r", encoding="utf-8", newline='') as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return None
    cols = []
    for h in header:
        nh = _normalize_header(h)
        mapped = mapping.get(nh) or mapping.get(h.strip().lower())
        # fuzzy fallback: if exact mapping not found, try substring matches against mapping keys
        if not mapped:
            for k, v in mapping.items():
                if k in nh or nh in k:
                    mapped = v
                    break
        # final fallback to normalized header name
        if not mapped:
            mapped = nh
        # skip obvious serial/id columns if CSV doesn't intend to provide them
        if mapped in ("state_id","district_id","id") and mapped not in HEADER_MAP.get(key, {}):
            # if mapping resolves to an id but user header is not a numeric id header, skip including it
            # (we want DB SERIAL to fill)
            continue
        cols.append(mapped)
    # ensure we have at least one column
    return cols if cols else None

def copy_csv_to_table(table, csv_path, cols=None):
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        return
    # if no explicit cols provided, infer from CSV header and mapping
    if cols is None:
        inferred = infer_columns_for_table(table, csv_path)
        if inferred:
            cols = inferred
            print(f"Inferred columns for {table}: {cols}")
        else:
            print(f"Could not infer columns for {csv_path}, aborting COPY for {table}.")
            return

    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn, open(csv_path, "r", encoding="utf-8") as f:
        cur = conn.cursor()
        # build a safe identifier list for COPY
        idents = [sql.Identifier(c) for c in cols]
        copy_sql = sql.SQL("COPY {table} ({cols}) FROM STDIN WITH CSV HEADER DELIMITER ','")
        copy_sql = copy_sql.format(table=sql.Identifier(table), cols=sql.SQL(', ').join(idents))
        try:
            cur.copy_expert(copy_sql.as_string(conn), f)
            conn.commit()
            print(f"Copied {csv_path} -> {table} (columns: {cols})")
        except Exception as e:
            conn.rollback()
            print(f"Error copying CSV to {table}: {e}")

def table_exists(conn, schema_table):
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (schema_table,))
        return cur.fetchone()[0] is not None


def create_temp_table_from_header(conn, temp_table, header_cols):
    """Create a temp table with all text columns derived from header names."""
    # sanitize column names: ensure valid SQL identifiers
    def _sanitize(name):
        n = name.strip()
        if not n:
            return 'col'
        n = re.sub(r'[^a-zA-Z0-9_]', '_', n)
        if re.match(r'^[0-9]', n):
            n = 'c_' + n
        return n

    cols = [_sanitize(c) for c in header_cols]
    # build column definitions safely
    col_defs = [sql.SQL("{} TEXT").format(sql.Identifier(c)) for c in cols]
    create_sql = sql.SQL("DROP TABLE IF EXISTS {table}; CREATE TABLE {table} ({cols});").format(
        table=sql.Identifier(temp_table), cols=sql.SQL(', ').join(col_defs)
    )
    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()
    print(f"Created staging table {temp_table} with columns: {cols}")


def load_csv_to_temp_table(temp_table, csv_path, header_cols):
    """Load CSV into a temp table using COPY (columns must match header_cols)."""
    # sanitize header_cols in the same way create_temp_table_from_header did
    def _sanitize(name):
        n = name.strip()
        if not n:
            return 'col'
        n = re.sub(r'[^a-zA-Z0-9_]', '_', n)
        if re.match(r'^[0-9]', n):
            n = 'c_' + n
        return n

    sanitized = [_sanitize(c) for c in header_cols]
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn, open(csv_path, 'r', encoding='utf-8') as fh:
        cur = conn.cursor()
        idents = [sql.Identifier(c) for c in sanitized]
        copy_sql = sql.SQL("COPY {table} ({cols}) FROM STDIN WITH CSV HEADER DELIMITER ','").format(
            table=sql.Identifier(temp_table), cols=sql.SQL(', ').join(idents)
        )
        try:
            cur.copy_expert(copy_sql.as_string(conn), fh)
            conn.commit()
            print(f"Loaded {csv_path} into temp table {temp_table}")
        except Exception as e:
            conn.rollback()
            print(f"Failed loading temp table {temp_table}: {e}")
    return sanitized


def transform_states_from_temp(temp_table, sanitized_cols):
    """Transform and insert data from temp table into states: cast numeric fields and avoid inserting serials.
    sanitized_cols should be a list of column names in the temp table in the same order as CSV header.
    """
    # build mapping set for quick lookup
    colset = set(sanitized_cols)
    # target columns in final table and corresponding expected temp column names
    target_cols = [
        ('state_name', ['state', 'state_name']),
        ('population', ['population']),
        ('population_percent', ['population_percent']),
        ('male', ['male']),
        ('female', ['female']),
        ('rural', ['rural']),
        ('urban', ['urban']),
        ('area_km2', ['area_km2']),
        ('population_density', ['population_density_per_km2', 'population_density']),
        ('est_unemployment_rate', ['estimated_unemployment_rate_percent', 'estimated_unemployment_rate']),
        ('est_employed', ['estimated_employed', 'est_employed']),
        ('area_type', ['area_type'])
    ]

    select_exprs = []
    found_map = {}
    for tgt, candidates in target_cols:
        found = None
        for c in candidates:
            if c in colset:
                found = c
                break
            # fuzzy substring match (e.g., 'rural_51_' should match 'rural')
            for col in colset:
                if c in col or col in c:
                    found = col
                    break
            if found:
                break
        found_map[tgt] = found
        if not found:
            # no source column; insert NULL
            select_exprs.append(sql.SQL('NULL'))
            continue
        # decide casting based on target
        if not found:
            select_exprs.append(sql.SQL('NULL'))
            continue
        if tgt in ('state_name', 'area_type'):
            # text fields
            select_exprs.append(sql.SQL("NULLIF(t.{col}, '')::TEXT").format(col=sql.Identifier(found)))
        elif tgt in ('population', 'male', 'female', 'rural', 'urban', 'est_employed'):
            # bigints: remove commas, round float-like values and convert to BIGINT
            select_exprs.append(sql.SQL("CAST(ROUND(NULLIF(REPLACE(t.{col}, ',', ''), '')::NUMERIC) AS BIGINT)").format(col=sql.Identifier(found)))
        else:
            # numeric fields
            select_exprs.append(sql.SQL("NULLIF(REPLACE(t.{col}, ',', ''), '')::NUMERIC").format(col=sql.Identifier(found)))

    fields_ident = [sql.Identifier(t[0]) for t in target_cols]
    non_key_idents = [sql.Identifier(t[0]) for t in target_cols if t[0] != 'state_name']
    # deduplicate by state_name inside a subquery to avoid "ON CONFLICT DO UPDATE command cannot affect row a second time"
    # determine source state column for DISTINCT ON
    state_src = found_map.get('state_name')
    if state_src:
        subquery = sql.SQL("(SELECT DISTINCT ON (t.{state}) t.* FROM {temp} t ORDER BY t.{state})").format(
            state=sql.Identifier(state_src), temp=sql.Identifier(temp_table)
        )
    else:
        subquery = sql.Identifier(temp_table)

    insert_sql = sql.SQL("INSERT INTO states ({fields}) SELECT {exprs} FROM {subq} AS t ON CONFLICT (state_name) DO UPDATE SET {updates};").format(
        fields=sql.SQL(', ').join(fields_ident),
        exprs=sql.SQL(', ').join(select_exprs),
        subq=subquery,
        updates=sql.SQL(', ').join([
            sql.SQL("{col} = EXCLUDED.{col}").format(col=ident) for ident in non_key_idents
        ])
    )

    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(insert_sql)
                conn.commit()
                print("Inserted states from temp table")
            except Exception as e:
                conn.rollback()
                print(f"Error inserting states from temp: {e}")


def transform_districts_from_temp(temp_table, sanitized_cols):
    """Transform temp districts: resolve state name to state_id and insert into districts.
    sanitized_cols should be a list of column names in the temp table in the same order as CSV header.
    """
    colset = set(sanitized_cols)
    district_col = 'district' if 'district' in colset else ('district_name' if 'district_name' in colset else None)
    state_col = 'state' if 'state' in colset else ('state_name' if 'state_name' in colset else None)
    pop_col = 'population_district' if 'population_district' in colset else ('population' if 'population' in colset else None)
    lit_col = 'literacy_rate_percent' if 'literacy_rate_percent' in colset else ('literacy' if 'literacy' in colset else None)
    if not district_col:
        print("Could not find district column in temp table; skipping districts transform")
        return

    select_exprs = []
    # district_name
    select_exprs.append(sql.SQL("NULLIF(t.{c}, '')::TEXT").format(c=sql.Identifier(district_col)))
    # state_id via join
    if state_col:
        # we'll reference s.state_id after left join
        select_exprs.append(sql.SQL("s.state_id"))
    else:
        select_exprs.append(sql.SQL("NULL"))
    # population_district (bigint) - remove commas
    if pop_col:
        select_exprs.append(sql.SQL("NULLIF(REPLACE(t.{c}, ',', ''), '')::BIGINT").format(c=sql.Identifier(pop_col)))
    else:
        select_exprs.append(sql.SQL("NULL"))
    # literacy_rate (numeric)
    if lit_col:
        select_exprs.append(sql.SQL("NULLIF(REPLACE(t.{c}, ',', ''), '')::NUMERIC").format(c=sql.Identifier(lit_col)))
    else:
        select_exprs.append(sql.SQL("NULL"))

    from_clause = sql.SQL("{temp} t").format(temp=sql.Identifier(temp_table))
    if state_col:
        from_clause = sql.SQL("{temp} t LEFT JOIN states s ON t.{state_col} = s.state_name").format(
            temp=sql.Identifier(temp_table), state_col=sql.Identifier(state_col)
        )

    insert_sql = sql.SQL("INSERT INTO districts (district_name, state_id, population_district, literacy_rate) SELECT {exprs} FROM {from_clause};").format(
        exprs=sql.SQL(', ').join(select_exprs), from_clause=from_clause
    )

    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(insert_sql)
                conn.commit()
                print("Inserted districts from temp table")
            except Exception as e:
                conn.rollback()
                print(f"Error inserting districts from temp: {e}")

def update_states_geom_from_imported(table_geom):
    # check that imported table exists before attempting update
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        if not table_exists(conn, f"public.{table_geom}"):
            print(f"Table public.{table_geom} does not exist; skipping geom update.")
            return
        # inspect columns of the imported table to find a candidate name column
        with conn.cursor() as cur:
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = %s",
                (table_geom,)
            )
            cols = [r[0] for r in cur.fetchall()]

        # normalize and map original names
        norm = {c.lower(): c for c in cols}
        # common attribute names used by shapefiles for state name
        candidates = ['state_name', 'name', 'name_1', 'st_nm', 'st_name', 'state', 'state_nm', 'st', 'admin_name', 'adm1_name', 'NAME_1', 'NAME']
        chosen = None
        for cand in candidates:
            if cand.lower() in norm:
                chosen = norm[cand.lower()]
                break
        if not chosen:
            print(f"Could not find a name column in public.{table_geom} (searched: {candidates}). Columns: {cols}")
            print("Skipping geom update. You can inspect public.%s to see the correct attribute column." % table_geom)
            return

        # build update SQL using the discovered column name
        update_sql = sql.SQL(
            "UPDATE states s\n"
            "SET geom = g.geom\n"
            "FROM public.{geom_table} g\n"
            "WHERE s.state_name ILIKE g.{name_col} OR s.state_name = g.{name_col};"
        ).format(geom_table=sql.Identifier(table_geom), name_col=sql.Identifier(chosen))
        with conn.cursor() as cur:
            cur.execute(update_sql)
        conn.commit()
        print(f"Updated states.geom from public.{table_geom}")


def import_shapefile_to_table(shp_path, target_table):
    """Import a shapefile using shp2pgsql and psql (Windows-friendly)."""
    if not shp_path or not os.path.exists(shp_path):
        print(f"Shapefile not found: {shp_path}")
        return
    shp2pgsql = os.path.join(CFG["pg_bin"], "shp2pgsql.exe")
    psql = os.path.join(CFG["pg_bin"], "psql.exe")
    if not os.path.exists(shp2pgsql) or not os.path.exists(psql):
        print("shp2pgsql or psql not found in pg_bin. Edit CFG['pg_bin'].")
        return
    env = os.environ.copy()
    env["PGPASSWORD"] = CFG["pg_password"]
    cmd = f'"{shp2pgsql}" -I -s 4326 "{shp_path}" public.{target_table} | "{psql}" -h {CFG["pg_host"]} -p {CFG["pg_port"]} -U {CFG["pg_user"]} -d {CFG["dbname"]}'
    print("Running shapefile import:", cmd)
    res = subprocess.run(cmd, shell=True, env=env)
    if res.returncode == 0:
        print(f"Shapefile {shp_path} imported as public.{target_table}")
    else:
        print(f"Error importing shapefile (returncode={res.returncode})")


def update_districts_geom_from_imported(table_geom):
    """Update districts.geom from an imported shapefile table. Attempts to detect the name column and match to districts.district_name."""
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
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
            "UPDATE districts d SET geom = g.geom FROM public.{geom_table} g WHERE d.district_name ILIKE g.{name_col} OR d.district_name = g.{name_col};"
        ).format(geom_table=sql.Identifier(table_geom), name_col=sql.Identifier(chosen))
        with conn.cursor() as cur:
            cur.execute(update_sql)
        conn.commit()
        print(f"Updated districts.geom from public.{table_geom}")

def run_test_spatial_queries(limit=5):
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        cur = conn.cursor()
        print("Sample ST_Centroid for states (first rows):")
        cur.execute("SELECT state_name, ST_AsText(ST_Centroid(geom)) FROM states WHERE geom IS NOT NULL LIMIT %s", (limit,))
        for row in cur.fetchall():
            print(row[0], row[1])
        print("\nArea (ST_Area) for sample states:")
        cur.execute("SELECT state_name, ST_Area(geom::geography) AS area_m2 FROM states WHERE geom IS NOT NULL LIMIT %s", (limit,))
        for row in cur.fetchall():
            print(row[0], f"{row[1]:,.0f} m2")

def main():
    # ensure pg_bin is valid or auto-detect it
    CFG['pg_bin'] = r"C:\Program Files\PostgreSQL\17\bin"
    if CFG["create_db"]:
        create_database_if_missing()
    enable_postgis_extensions()
    create_core_tables()

    s_header = None
    try:
        with open(CFG["csv_states_1"], 'r', encoding='utf-8') as fh:
            s_header = next(csv.reader(fh))
    except Exception:
        s_header = None
    if s_header:
        s_cols = [_normalize_header(h) for h in s_header]
        temp_states = "temp_states"
        with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
            create_temp_table_from_header(conn, temp_states, s_cols)
        sanitized_states = load_csv_to_temp_table(temp_states, CFG["csv_states_1"], s_cols)
        transform_states_from_temp(temp_states, sanitized_states)
    else:
        print("Could not read states CSV header; skipping states load.")

    # DISTRICTS
    d_header = None
    try:
        with open(CFG["csv_districts"], 'r', encoding='utf-8') as fh:
            d_header = next(csv.reader(fh))
    except Exception:
        d_header = None
    if d_header:
        d_cols = [_normalize_header(h) for h in d_header]
        temp_districts = "temp_districts"
        with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
            create_temp_table_from_header(conn, temp_districts, d_cols)
        sanitized_districts = load_csv_to_temp_table(temp_districts, CFG["csv_districts"], d_cols)
        transform_districts_from_temp(temp_districts, sanitized_districts)
    else:
        print("Could not read districts CSV header; skipping districts load.")
    copy_csv_to_table("expenditures", CFG["csv_expenditures"])
    copy_csv_to_table("employment", CFG["csv_employment"])
    copy_csv_to_table("customers", CFG["csv_customers"])

    import_shapefile_to_table(CFG["shp_states"], "states_geom")
    update_states_geom_from_imported("states_geom")

    import_shapefile_to_table(CFG.get("shp_districts"), "districts_geom")
    update_districts_geom_from_imported("districts_geom")

    run_test_spatial_queries()

if __name__ == "__main__":
    main()