import getpass
import socket
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command

try:
    import psycopg2
    from psycopg2 import OperationalError, sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError as exc:  # pragma: no cover - handled at runtime
    psycopg2 = None
    OperationalError = None
    ISOLATION_LEVEL_AUTOCOMMIT = None
    sql = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


def _clean(value: Optional[str]) -> Optional[str]:
    return value or None


def _get_db_params(db_conf: Dict[str, Any]) -> Dict[str, Optional[str]]:
    return {
        "dbname": db_conf.get("NAME"),
        "user": _clean(db_conf.get("USER") or getpass.getuser()),
        "password": _clean(db_conf.get("PASSWORD")),
        "host": _clean(db_conf.get("HOST") or "localhost"),
        "port": _clean(str(db_conf.get("PORT")) if db_conf.get("PORT") else "5432"),
    }


class Command(BaseCommand):
    help = "Ensure the PostGIS database exists, enable the extension, apply migrations, and seed synthetic data."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--skip-migrate",
            action="store_true",
            help="Skip running Django migrations after preparing the database.",
        )
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="Skip generating synthetic geo datasets after migrations.",
        )
        parser.add_argument(
            "--skip-shapefiles",
            action="store_true",
            help="Skip importing official shapefiles after migrations.",
        )
        parser.add_argument(
            "--strict-shapefiles",
            action="store_true",
            help="Raise an error if shapefile import fails (defaults to warning).",
        )
        parser.add_argument(
            "--states-shapefile",
            type=str,
            default="",
            help="Override path to the states shapefile.",
        )
        parser.add_argument(
            "--districts-shapefile",
            type=str,
            default="",
            help="Override path to the districts shapefile.",
        )
        parser.add_argument(
            "--records",
            type=int,
            default=10000,
            help="Minimum number of synthetic demographic profiles to generate (default: 10000).",
        )
        parser.add_argument(
            "--reset-data",
            action="store_true",
            help="Reset existing geo data before seeding synthetic records.",
        )
        parser.add_argument(
            "--maintenance-db",
            type=str,
            default="postgres",
            help="Maintenance database to connect for CREATE DATABASE (default: postgres).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if psycopg2 is None:
            raise CommandError(
                "psycopg2 is required for setup_postgis_db. Install dependencies with 'pip install -r requirements.txt'."
            ) from IMPORT_ERROR

        db_conf = settings.DATABASES.get("default")
        if not db_conf:
            raise CommandError("No default database configuration found.")

        params = _get_db_params(db_conf)
        if not params.get("dbname"):
            raise CommandError("Database NAME must be provided in settings.DATABASES['default'].")

        self.stdout.write(self.style.NOTICE(f"Preparing database '{params['dbname']}' on {params['host'] or 'localhost'}..."))
        self._ensure_database(params, options["maintenance_db"], db_conf)
        self._ensure_extension(params)

        if not options["skip_migrate"]:
            self.stdout.write(self.style.NOTICE("Applying Django migrations..."))
            call_command("migrate", interactive=False)

        shapefile_imported = False
        if not options["skip_shapefiles"]:
            shapefile_kwargs: Dict[str, Any] = {}
            if options["states_shapefile"]:
                shapefile_kwargs["states"] = options["states_shapefile"]
            if options["districts_shapefile"]:
                shapefile_kwargs["districts"] = options["districts_shapefile"]
            if options["reset_data"]:
                shapefile_kwargs["reset"] = True

            try:
                self.stdout.write(self.style.NOTICE("Importing state and district shapefiles..."))
                call_command("import_geo_shapefiles", **shapefile_kwargs)
                shapefile_imported = True
            except CommandError as exc:
                message = f"Shapefile import skipped: {exc}"
                if options["strict_shapefiles"]:
                    raise CommandError(message) from exc
                self.stdout.write(self.style.WARNING(message))

        if not options["skip_seed"]:
            seed_options = {"records": options["records"]}
            if options["reset_data"]:
                seed_options["reset"] = True
            if shapefile_imported:
                seed_options["preserve_districts"] = True
            self.stdout.write(self.style.NOTICE("Generating synthetic geo datasets..."))
            call_command("generate_synthetic_geo_data", **seed_options)

        self.stdout.write(self.style.SUCCESS("PostGIS environment is ready."))

    def _ensure_database(self, params: Dict[str, Optional[str]], maintenance_db: str, db_conf: Dict[str, Any]) -> None:
        admin_params = params.copy()
        admin_params["dbname"] = maintenance_db

        options = db_conf.get("OPTIONS", {})
        sslmode = options.get("sslmode")
        if sslmode:
            admin_params["sslmode"] = sslmode

        try:
            conn = psycopg2.connect(**admin_params)
        except OperationalError as exc:
            raise CommandError(f"Unable to create database '{params['dbname']}': {exc}") from exc

        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (params["dbname"],))
                exists = cursor.fetchone() is not None
                if exists:
                    self.stdout.write(self.style.SUCCESS(f"Database '{params['dbname']}' already exists."))
                    return
                cursor.execute(
                    sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(sql.Identifier(params["dbname"]))
                )
        except OperationalError as exc:
            raise CommandError(f"Unable to create database '{params['dbname']}': {exc}") from exc
        finally:
            conn.close()

        self.stdout.write(self.style.SUCCESS(f"Created database '{params['dbname']}'."))

    def _ensure_extension(self, params: Dict[str, Optional[str]]) -> None:
        try:
            conn = psycopg2.connect(**params)
        except OperationalError as exc:
            host = params.get("host") or socket.gethostname()
            raise CommandError(
                f"Failed to enable PostGIS extension on '{params['dbname']}' at {host}: {exc}"
            ) from exc

        try:
            conn.autocommit = True
            with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        except OperationalError as exc:
            host = params.get("host") or socket.gethostname()
            raise CommandError(
                f"Failed to enable PostGIS extension on '{params['dbname']}' at {host}: {exc}"
            ) from exc
        finally:
            conn.close()

        self.stdout.write(self.style.SUCCESS("PostGIS extension ensured."))
