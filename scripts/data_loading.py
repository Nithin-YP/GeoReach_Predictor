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
    "pg_user": os.environ.get("PG_USER", os.environ.get("PGUSER", "postgres")),
    "pg_password": os.environ.get("PG_PASSWORD", os.environ.get("PGPASSWORD", "postgres")),
    "create_db": _env_bool("CREATE_DB", True),
    "dbname": os.environ.get("PG_DBNAME", os.environ.get("PGDATABASE", "georeach_db")),
    "pg_bin": os.environ.get("PG_BIN", r"C:\\Program Files\\PostgreSQL\\17\\bin"),
    # CSV files (example relative paths on Windows) - these can be overridden in .env
    "csv_states_1": os.environ.get("CSV_STATES_1", r"..\\datasets\\geodata\\dataset1.csv"),
    "csv_districts": os.environ.get("CSV_DISTRICTS", r"..\\datasets\\geodata\\dataset2.csv"),
    "csv_expenditures": os.environ.get("CSV_EXPENDITURES", r"..\\datasets\\geodata\\dataset3.csv"),
    "csv_employment": os.environ.get("CSV_EMPLOYMENT", r"..\\datasets\\geodata\\dataset5.csv"),
    "csv_customers": os.environ.get("CSV_CUSTOMERS", r"..\\datasets\\geodata\\dataset6.csv"),
    "csv_city_to_state": os.environ.get("CSV_CITY_TO_STATE", r"..\\datasets\\city_to_state_mapping.csv"),
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
        -- Granularity columns (STATE/DISTRICT only)
        state_name VARCHAR(100),
        district_name VARCHAR(100),
        state_id INT,
        district_id INT,
        -- Original columns
        income NUMERIC,
        age INT,
        occupation VARCHAR(100),
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
        potential_savings_misc NUMERIC,
        FOREIGN KEY (state_id) REFERENCES states(state_id),
        FOREIGN KEY (district_id) REFERENCES districts(district_id)
    );

    CREATE TABLE IF NOT EXISTS employment (
        id SERIAL PRIMARY KEY,
        -- Granularity columns (STATE/DISTRICT only)
        state_name VARCHAR(100),
        district_name VARCHAR(100),
        state_id INT,
        district_id INT,
        -- Original columns
        employment_status VARCHAR(100),
        age_group VARCHAR(50),
        education_level VARCHAR(50),
        industry VARCHAR(100),
        location VARCHAR(100),
        monthly_salary_inr NUMERIC,
        FOREIGN KEY (state_id) REFERENCES states(state_id),
        FOREIGN KEY (district_id) REFERENCES districts(district_id)
    );

    CREATE TABLE IF NOT EXISTS customers (
        id SERIAL PRIMARY KEY,
        -- Granularity columns (STATE/DISTRICT only)
        state_name VARCHAR(100),
        district_name VARCHAR(100),
        state_id INT,
        district_id INT,
        -- Original columns
        customer_name VARCHAR(100),
        age INT,
        gender VARCHAR(20),
        education_level VARCHAR(50),
        income NUMERIC,
        purchase_frequency NUMERIC,
        spending NUMERIC,
        FOREIGN KEY (state_id) REFERENCES states(state_id),
        FOREIGN KEY (district_id) REFERENCES districts(district_id)
    );

    -- Create indices for better query performance
    CREATE INDEX IF NOT EXISTS idx_expenditures_state ON expenditures(state_id);
    CREATE INDEX IF NOT EXISTS idx_expenditures_district ON expenditures(district_id);
    
    CREATE INDEX IF NOT EXISTS idx_employment_state ON employment(state_id);
    CREATE INDEX IF NOT EXISTS idx_employment_district ON employment(district_id);
    
    CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(state_id);
    CREATE INDEX IF NOT EXISTS idx_customers_district ON customers(district_id);
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
        # Granularity columns (STATE/DISTRICT only)
        "state": "state_name",
        "state_name": "state_name",
        "district": "district_name",
        "district_name": "district_name",
        # map common verbose headers to compact table columns
        "income": "income",
        "age": "age",
        "occupation": "occupation",
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
        # Granularity columns (STATE/DISTRICT only)
        "state": "state_name",
        "state_name": "state_name",
        "district": "district_name",
        "district_name": "district_name",
        # Original columns
        "employment_status": "employment_status",
        "age_group": "age_group",
        "education_level": "education_level",
        "industry": "industry",
        "location": "location",
        "monthly_salary_inr": "monthly_salary_inr",
    },
    "customers": {
        # Granularity columns (STATE/DISTRICT only)
        "state": "state_name",
        "state_name": "state_name",
        "district": "district_name",
        "district_name": "district_name",
        # Original columns
        "customer_name": "customer_name",
        "age": "age",
        "gender": "gender",
        "education_level": "education_level",
        "income": "income",
        "purchase_frequency": "purchase_frequency",
        "spending": "spending",
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
    """
    DEPRECATED: Use transform functions instead for better data quality.
    Direct COPY can fail with numeric formatting, commas, nulls, etc.
    This is kept for backwards compatibility but logs a warning.
    """
    if not os.path.exists(csv_path):
        print(f"CSV not found: {csv_path}")
        return
    
    print(f"\n⚠️  WARNING: Using direct COPY for {table}")
    print(f"   Recommended: Use transform functions for {table} instead")
    print(f"   Direct COPY may fail with formatted numbers (e.g., '1,000' or '$50')")
    print(f"   Continuing with direct COPY...\n")
    
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
            print(f"✅ Copied {csv_path} -> {table} (columns: {cols})")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error copying CSV to {table}: {e}")
            print(f"   Consider creating a transform function for this table")

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
    """Import a shapefile using shp2pgsql and psql (Windows-friendly) with fallback guidance."""
    if not shp_path or not os.path.exists(shp_path):
        print(f"\n⚠️  Shapefile not found: {shp_path}")
        print(f"\n📥 SHAPEFILE DOWNLOAD GUIDE:")
        print(f"   You can download Indian state/district shapefiles from:")
        print(f"   1. GADM: https://gadm.org/download_country.html (Select India)")
        print(f"   2. DataMeet: https://github.com/datameet/maps")
        print(f"   3. Natural Earth: https://www.naturalearthdata.com/")
        print(f"\n   Save to: datasets/geodata/")
        print(f"   Expected files: india_states.shp, india_districts.shp")
        print(f"   (+ associated .shx, .dbf, .prj files)")
        print(f"\n   Continuing without shapefile geometry...\n")
        return False
    
    shp2pgsql = os.path.join(CFG["pg_bin"], "shp2pgsql.exe")
    psql = os.path.join(CFG["pg_bin"], "psql.exe")
    if not os.path.exists(shp2pgsql) or not os.path.exists(psql):
        print("\n⚠️  shp2pgsql or psql not found in pg_bin.")
        print(f"   Current pg_bin: {CFG['pg_bin']}")
        print(f"   Please install PostgreSQL with PostGIS or update CFG['pg_bin'].")
        print(f"   Continuing without shapefile geometry...\n")
        return False
    
    env = os.environ.copy()
    env["PGPASSWORD"] = CFG["pg_password"]
    cmd = f'"{shp2pgsql}" -I -s 4326 "{shp_path}" public.{target_table} | "{psql}" -h {CFG["pg_host"]} -p {CFG["pg_port"]} -U {CFG["pg_user"]} -d {CFG["dbname"]}'
    print(f"Running shapefile import: {target_table}")
    res = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"✅ Shapefile imported as public.{target_table}")
        return True
    else:
        print(f"❌ Error importing shapefile (returncode={res.returncode})")
        if res.stderr:
            print(f"   Error details: {res.stderr[:200]}")
        return False


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
            "UPDATE districts d SET geom = g.geom FROM public.{geom_table} g WHERE d.district_name ILIKE g.{name_col} OR d.district_name = g.{name_col};"
        ).format(geom_table=sql.Identifier(table_geom), name_col=sql.Identifier(chosen))
        with conn.cursor() as cur:
            cur.execute(update_sql)
        conn.commit()
        print(f"Updated districts.geom from public.{table_geom}")


def resolve_granularity_foreign_keys(table_name):
    """
    After loading data, resolve state_name/district_name to their IDs.
    This enables proper foreign key relationships and aggregation queries.
    (STATE/DISTRICT only - NO CITY)
    """
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        cur = conn.cursor()
        
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


def load_city_to_state_mapping():
    """
    Create buffered polygon geometries for cities based on their point locations.
    This improves spatial joins by giving cities an area instead of just a point.
    
    buffer_km: Radius in kilometers to buffer around city center point
    """
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        cur = conn.cursor()
        
        # Check if cities have locations
        cur.execute("SELECT COUNT(*) FROM cities WHERE location IS NOT NULL")
        city_count = cur.fetchone()[0]
        
        if city_count == 0:
            print("⚠️  No cities with location points found. Skipping buffer creation.")
            return
        
        print(f"\n🗺️  Creating {buffer_km}km buffer polygons for {city_count} cities...")
        
        # Create buffered geometries from point locations
        # ST_Buffer on geography gives us accurate metric buffers
        buffer_sql = """
            UPDATE cities
            SET geom = ST_Multi(
                ST_Transform(
                    ST_Buffer(location::geography, %s)::geometry,
                    4326
                )
            )
            WHERE location IS NOT NULL AND geom IS NULL
        """
        
        try:
            buffer_meters = buffer_km * 1000
            cur.execute(buffer_sql, (buffer_meters,))
            updated_count = cur.rowcount
            conn.commit()
            print(f"✅ Created buffer polygons for {updated_count} cities")
            print(f"   Buffer radius: {buffer_km}km")
            print(f"   This enables better spatial joins and 'within city' queries")
        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating city buffers: {e}")


def create_geo_hierarchy_view():
    """
    Create a materialized view that shows the geographic hierarchy (STATE/DISTRICT only).
    Useful for debugging and visual inspection of relationships.
    """
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        cur = conn.cursor()
        
        print("\n📊 Creating geo_hierarchy materialized view...")
        
        view_sql = """
            DROP MATERIALIZED VIEW IF EXISTS geo_hierarchy CASCADE;
            
            CREATE MATERIALIZED VIEW geo_hierarchy AS
            SELECT 
                -- State info
                s.state_id,
                s.state_name,
                s.population as state_population,
                s.area_km2 as state_area_km2,
                s.population_density as state_density,
                
                -- District info
                d.district_id,
                d.district_name,
                d.population_district,
                d.literacy_rate as district_literacy_rate,
                
                -- Geometries (for GIS tools)
                s.geom as state_geom,
                d.geom as district_geom,
                
                -- Computed fields
                CASE 
                    WHEN d.district_id IS NOT NULL THEN 'district'
                    ELSE 'state'
                END as finest_granularity,
                
                -- Spatial relationships
                CASE 
                    WHEN d.geom IS NOT NULL AND s.geom IS NOT NULL THEN
                        ST_Intersects(d.geom, s.geom)
                    ELSE NULL
                END as district_in_state_check
                
            FROM states s
            LEFT JOIN districts d ON d.state_id = s.state_id;
            
            -- Create indices on the materialized view
            CREATE INDEX idx_geo_hierarchy_state ON geo_hierarchy(state_id);
            CREATE INDEX idx_geo_hierarchy_district ON geo_hierarchy(district_id);
            CREATE INDEX idx_geo_hierarchy_granularity ON geo_hierarchy(finest_granularity);
        """
        
        try:
            cur.execute(view_sql)
            conn.commit()
            
            # Get statistics
            cur.execute("SELECT COUNT(*) FROM geo_hierarchy")
            total_rows = cur.fetchone()[0]
            
            cur.execute("SELECT finest_granularity, COUNT(*) FROM geo_hierarchy GROUP BY finest_granularity ORDER BY finest_granularity")
            granularity_stats = cur.fetchall()
            
            print(f"✅ Created geo_hierarchy view with {total_rows} rows")
            print(f"\n   Granularity breakdown:")
            for gran, count in granularity_stats:
                print(f"   - {gran}: {count} records")
            
            print(f"\n   Usage:")
            print(f"   SELECT * FROM geo_hierarchy WHERE state_name = 'Maharashtra';")
            print(f"   SELECT * FROM geo_hierarchy WHERE district_name = 'Mumbai';")
            print(f"   \n   To refresh: REFRESH MATERIALIZED VIEW geo_hierarchy;")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error creating geo_hierarchy view: {e}")


def run_test_spatial_queries(limit=5):
    with psycopg2.connect(**conn_params(dbname=CFG["dbname"])) as conn:
        cur = conn.cursor()
        print("\n=== SPATIAL QUERY TESTS (STATE/DISTRICT LEVEL) ===")
        print("\nSample ST_Centroid for states (first rows):")
        cur.execute("SELECT state_name, ST_AsText(ST_Centroid(geom)) FROM states WHERE geom IS NOT NULL LIMIT %s", (limit,))
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        print("\nArea (ST_Area) for sample states:")
        cur.execute("SELECT state_name, ST_Area(geom::geography) AS area_m2 FROM states WHERE geom IS NOT NULL LIMIT %s", (limit,))
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]:,.0f} m²")
        
        # Test granularity aggregation
        print("\n=== GRANULARITY TEST: Employment by State ===")
        cur.execute("""
            SELECT s.state_name, COUNT(*) as records, 
                   AVG(e.monthly_salary_inr) as avg_salary
            FROM employment e
            JOIN states s ON e.state_id = s.state_id
            WHERE e.state_id IS NOT NULL
            GROUP BY s.state_name
            ORDER BY records DESC
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f"  {row[0]}: {row[1]} records, Avg Salary: ₹{row[2]:,.0f}" if row[2] else f"  {row[0]}: {row[1]} records")
        
        print("\n=== GRANULARITY TEST: Employment by District ===")
        cur.execute("""
            SELECT d.district_name, s.state_name, COUNT(*) as records, 
                   AVG(e.monthly_salary_inr) as avg_salary
            FROM employment e
            JOIN districts d ON e.district_id = d.district_id
            JOIN states s ON d.state_id = s.state_id
            WHERE e.district_id IS NOT NULL
            GROUP BY d.district_name, s.state_name
            ORDER BY records DESC
            LIMIT 5
        """)
        results = cur.fetchall()
        if results:
            for row in results:
                print(f"  {row[0]}, {row[1]}: {row[2]} records, Avg Salary: ₹{row[3]:,.0f}" if row[3] else f"  {row[0]}, {row[1]}: {row[2]} records")
        else:
            print("  (No district-level employment data yet)")
        
        # Test geo_hierarchy view if it exists
        print("\n=== GEO_HIERARCHY VIEW TEST ===")
        try:
            cur.execute("SELECT COUNT(*) FROM geo_hierarchy")
            view_count = cur.fetchone()[0]
            print(f"  geo_hierarchy view has {view_count} rows")
            
            cur.execute("""
                SELECT state_name, COUNT(DISTINCT district_name) as district_count
                FROM geo_hierarchy 
                WHERE district_name IS NOT NULL
                GROUP BY state_name
                ORDER BY district_count DESC
                LIMIT 5
            """)
            print("  Top states by district count:")
            for row in cur.fetchall():
                print(f"    {row[0]}: {row[1]} districts")
        except Exception as e:
            print(f"  geo_hierarchy view not available: {e}")
        
        print("\n=== DATA LOADING COMPLETE (STATE/DISTRICT LEVEL ONLY) ===\n")

def main():
    # ensure pg_bin is valid or auto-detect it
    CFG['pg_bin'] = r"C:\Program Files\PostgreSQL\17\bin"
    if CFG["create_db"]:
        create_database_if_missing()
    enable_postgis_extensions()
    create_core_tables()

    print("\n=== LOADING STATES ===")
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

    print("\n=== LOADING DISTRICTS ===")
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
    
    print("\n=== LOADING DATA TABLES (STATE/DISTRICT LEVEL) ===")
    print("⚠️  Note: Using direct COPY. For production, consider transform functions.")
    copy_csv_to_table("expenditures", CFG["csv_expenditures"])
    copy_csv_to_table("employment", CFG["csv_employment"])
    copy_csv_to_table("customers", CFG["csv_customers"])
    
    print("\n=== MAPPING EMPLOYMENT LOCATIONS TO STATES ===")
    # Load city-to-state mapping and use it to resolve employment locations
    # city_to_state_map = load_city_to_state_mapping()
    # map_employment_location_to_state(city_to_state_map)  # Function not defined, commenting out
    
    print("\n=== RESOLVING GRANULARITY FOREIGN KEYS (STATE/DISTRICT) ===")
    # Resolve foreign keys for all data tables
    resolve_granularity_foreign_keys("expenditures")
    resolve_granularity_foreign_keys("employment")
    resolve_granularity_foreign_keys("customers")
    
    print("\n=== LOADING SPATIAL GEOMETRIES ===")
    states_imported = import_shapefile_to_table(CFG["shp_states"], "states_geom")
    if states_imported:
        update_states_geom_from_imported("states_geom")

    districts_imported = import_shapefile_to_table(CFG.get("shp_districts"), "districts_geom")
    if districts_imported:
        update_districts_geom_from_imported("districts_geom")
    
    print("\n=== CREATING DEBUGGING VIEWS ===")
    create_geo_hierarchy_view()

    run_test_spatial_queries()

if __name__ == "__main__":
    main()