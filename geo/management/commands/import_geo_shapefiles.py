import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from django.conf import settings
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management import BaseCommand, CommandError

from geo.models import District, State

STATE_NAME_FIELDS: Tuple[str, ...] = (
    "state_name",
    "state_ut",
    "state",
    "st_name",
    "st_nm",
    "name_1",
    "name",
)
STATE_CODE_FIELDS: Tuple[str, ...] = (
    "state_code",
    "st_code",
    "state_ut",
    "hasc_1",
    "id",
)

DISTRICT_NAME_FIELDS: Tuple[str, ...] = (
    "district",
    "district_n",
    "district_",
    "district_nam",
    "district_na",
    "name_2",
    "name",
)
DISTRICT_STATE_FIELDS: Tuple[str, ...] = (
    "state",
    "state_nam",
    "state_name",
    "st_name",
    "st_nm",
    "name_1",
)
DISTRICT_CODE_FIELDS: Tuple[str, ...] = (
    "dist_code",
    "district_c",
    "id",
)


def _normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", str(value).strip())
    cleaned = cleaned.upper()
    cleaned = re.sub(r"[^A-Z0-9]+", "", cleaned)
    return cleaned


def _pick_field(fields: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    lowered = {field.lower(): field for field in fields}
    for candidate in candidates:
        key = candidate.lower()
        if key in lowered:
            return lowered[key]
    for field in fields:
        for candidate in candidates:
            if candidate.lower() in field.lower():
                return field
    return None


def _to_multipolygon(geometry: GEOSGeometry) -> MultiPolygon:
    if geometry.geom_type == "MultiPolygon":
        geom = geometry
    elif geometry.geom_type == "Polygon":
        geom = MultiPolygon(geometry)
    else:
        geom = geometry.convex_hull
        geom = geom if geom.geom_type == "MultiPolygon" else MultiPolygon(geom)
    geom.srid = 4326
    return geom


class Command(BaseCommand):
    help = "Import Indian state and district geometries from shapefiles into the geo models."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--states",
            type=str,
            default="",
            help="Path to the states shapefile (defaults to datasets/geodata/india_states.shp)",
        )
        parser.add_argument(
            "--districts",
            type=str,
            default="",
            help="Path to the districts shapefile (defaults to datasets/geodata/india_districts.shp)",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Purge existing State and District records before importing (cascades to related data).",
        )
        parser.add_argument(
            "--summary",
            action="store_true",
            help="Print a JSON summary of the import actions performed.",
        )

    def handle(self, *args, **options) -> None:
        base_dir = Path(settings.BASE_DIR)
        default_states = base_dir / "datasets" / "geodata" / "india_states.shp"
        default_districts = base_dir / "datasets" / "geodata" / "india_districts.shp"

        states_path = Path(options["states"] or default_states)
        districts_path = Path(options["districts"] or default_districts)

        if options["reset"]:
            self.stdout.write(self.style.WARNING("Resetting existing geographic data (this cascades to related tables)."))
            District.objects.all().delete()
            State.objects.all().delete()

        missing = [str(p) for p, key in ((states_path, "states"), (districts_path, "districts")) if not p.exists()]
        if missing:
            raise CommandError(f"The following shapefile paths were not found: {', '.join(missing)}")

        summary = {
            "states": self._import_states(states_path),
            "districts": self._import_districts(districts_path),
        }

        if options["summary"]:
            self.stdout.write(json.dumps(summary, indent=2))

    def _import_states(self, path: Path) -> Dict[str, int]:
        datasource = DataSource(str(path))
        if len(datasource) == 0:
            raise CommandError(f"No layers found in {path}")
        layer = datasource[0]
        name_field = _pick_field(layer.fields, STATE_NAME_FIELDS)
        if not name_field:
            raise CommandError("Unable to determine the state name field in the shapefile.")
        code_field = _pick_field(layer.fields, STATE_CODE_FIELDS)

        created = 0
        updated = 0
        for feature in layer:
            raw_name = feature.get(name_field)
            if not raw_name:
                continue
            name = str(raw_name).strip()
            raw_code = feature.get(code_field) if code_field else None
            code = str(raw_code).strip() if raw_code else None

            geom = feature.geom.clone()
            if geom.srs is not None and geom.srs.srid and geom.srs.srid != 4326:
                geom.transform(4326)
            geos = _to_multipolygon(geom.geos)

            defaults = {
                "code": code or None,
                "geometry": geos,
                "centroid": geos.centroid if not geos.empty else None,
            }
            state, was_created = State.objects.update_or_create(name=name, defaults=defaults)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(self.style.SUCCESS(f"States import complete: {created} created, {updated} updated."))
        return {"created": created, "updated": updated}

    def _import_districts(self, path: Path) -> Dict[str, int]:
        datasource = DataSource(str(path))
        if len(datasource) == 0:
            raise CommandError(f"No layers found in {path}")
        layer = datasource[0]
        name_field = _pick_field(layer.fields, DISTRICT_NAME_FIELDS)
        state_field = _pick_field(layer.fields, DISTRICT_STATE_FIELDS)
        if not name_field or not state_field:
            raise CommandError("Unable to determine district or state name fields in the shapefile.")
        code_field = _pick_field(layer.fields, DISTRICT_CODE_FIELDS)

        state_lookup: Dict[str, State] = { _normalize(state.name): state for state in State.objects.all() }

        created = 0
        updated = 0
        skipped = 0
        for feature in layer:
            raw_name = feature.get(name_field)
            raw_state = feature.get(state_field)
            if not raw_name or not raw_state:
                skipped += 1
                continue

            district_name = str(raw_name).strip()
            state_name = str(raw_state).strip()
            match_key = _normalize(state_name)
            state = state_lookup.get(match_key)
            if not state:
                skipped += 1
                continue

            geom = feature.geom.clone()
            if geom.srs is not None and geom.srs.srid and geom.srs.srid != 4326:
                geom.transform(4326)
            geos = _to_multipolygon(geom.geos)

            defaults = {
                "geometry": geos,
                "centroid": geos.centroid if not geos.empty else None,
            }
            district, was_created = District.objects.update_or_create(
                state=state,
                name=district_name,
                defaults=defaults,
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(self.style.SUCCESS(f"Districts import complete: {created} created, {updated} updated, {skipped} skipped."))
        return {"created": created, "updated": updated, "skipped": skipped}
