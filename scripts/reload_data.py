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
    "csv_expenditures": os.path.join(os.path.dirname(__file__), "..", "datasets", "geodata", "dataset3.csv"),
    "csv_employment": os.path.join(os.path.dirname(__file__), "..", "datasets", "geodata", "dataset5.csv"),
    "csv_customers": os.path.join(os.path.dirname(__file__), "..", "datasets", "geodata", "dataset6.csv"),
}

def conn_params():
    return {
        "host": CFG["pg_host"],
        "port": CFG["pg_port"],
        "user": CFG["pg_user"],
        "password": CFG["pg_password"],
        "dbname": CFG["dbname"],
    }

import csv
from io import StringIO

def copy_csv_to_table(table_name, csv_path):
    with psycopg2.connect(**conn_params()) as conn:
        cur = conn.cursor()
        with open(csv_path, 'r', newline='') as f:
            reader = csv.reader(f)
            header = next(reader)
        inferred_cols = [HEADER_MAP.get(table_name, {}).get(_normalize_header(h), _normalize_header(h)) for h in header]
        with open(csv_path, 'r', newline='') as f:
            lines = f.readlines()
        data = ''.join(lines[1:])  # skip header
        cur.copy_from(StringIO(data), table_name, columns=inferred_cols, sep=',')
        conn.commit()
        print(f"✅ Copied {csv_path} -> {table_name} (columns: {inferred_cols})")

HEADER_MAP = {
    "expenditures": {
        "state": "state_name",
        "district": "district_name",
        "income": "income",
        "age": "age",
        "occupation": "occupation",
        "groceries_exp": "groceries_exp",
        "transport_exp": "transport_exp",
        "eating_out_exp": "eating_out_exp",
        "entertainment_exp": "entertainment_exp",
        "utilities_exp": "utilities_exp",
        "healthcare_exp": "healthcare_exp",
        "education_exp": "education_exp",
        "misc_exp": "misc_exp",
        "disposable_income": "disposable_income",
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
        "state": "state_name",
        "district": "district_name",
        "employment_status": "employment_status",
        "age_group": "age_group",
        "education_level": "education_level",
        "industry": "industry",
        "location": "location",
        "monthly_salary_inr": "monthly_salary_inr",
    },
    "customers": {
        "state": "state_name",
        "district": "district_name",
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

import re

def main():
    copy_csv_to_table("expenditures", CFG["csv_expenditures"])
    copy_csv_to_table("employment", CFG["csv_employment"])
    copy_csv_to_table("customers", CFG["csv_customers"])

if __name__ == "__main__":
    main()