import csv
import math
import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import geopandas as gpd
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point, Polygon
from django.core.management import BaseCommand

from core.models import Dataset
from geo.models import (
    DemographicProfile,
    District,
    EconomicIndicator,
    IndustryEmployment,
    MarketPotentialZone,
    State,
)


STATE_DATA: Tuple[Tuple[str, str], ...] = (
    ("Andhra Pradesh", "AP"),
    ("Arunachal Pradesh", "AR"),
    ("Assam", "AS"),
    ("Bihar", "BR"),
    ("Chhattisgarh", "CG"),
    ("Goa", "GA"),
    ("Gujarat", "GJ"),
    ("Haryana", "HR"),
    ("Himachal Pradesh", "HP"),
    ("Jharkhand", "JH"),
    ("Karnataka", "KA"),
    ("Kerala", "KL"),
    ("Madhya Pradesh", "MP"),
    ("Maharashtra", "MH"),
    ("Manipur", "MN"),
    ("Meghalaya", "ML"),
    ("Mizoram", "MZ"),
    ("Nagaland", "NL"),
    ("Odisha", "OR"),
    ("Punjab", "PB"),
    ("Rajasthan", "RJ"),
    ("Sikkim", "SK"),
    ("Tamil Nadu", "TN"),
    ("Telangana", "TG"),
    ("Tripura", "TR"),
    ("Uttar Pradesh", "UP"),
    ("Uttarakhand", "UT"),
    ("West Bengal", "WB"),
    ("Andaman and Nicobar Islands", "AN"),
    ("Chandigarh", "CH"),
    ("Dadra and Nagar Haveli and Daman and Diu", "DN"),
    ("Delhi", "DL"),
    ("Jammu and Kashmir", "JK"),
    # ("Ladakh", "LA"),  # Excluded - not in shapefile, would show incorrect geometry
    ("Lakshadweep", "LD"),
    ("Puducherry", "PY"),
)

AGE_GROUPS: Tuple[str, ...] = tuple(choice[0] for choice in DemographicProfile.AGE_GROUP_CHOICES)
EDUCATION_LEVELS: Tuple[str, ...] = tuple(choice[0] for choice in DemographicProfile.EDUCATION_CHOICES)
AREA_TYPES: Tuple[str, ...] = tuple(choice[0] for choice in EconomicIndicator.AREA_CHOICES)
INDUSTRIES: Tuple[str, ...] = tuple(choice[0] for choice in IndustryEmployment.INDUSTRY_CHOICES)
POTENTIAL_LEVELS: Tuple[str, ...] = tuple(choice[0] for choice in MarketPotentialZone.POTENTIAL_LEVEL_CHOICES)
OCCUPATIONS: Tuple[str, ...] = (
    "Salaried",
    "Self-Employed",
    "Agriculture",
    "Student",
    "Retired",
    "Gig Worker",
    "Unemployed",
)
PRODUCT_TYPES: Tuple[str, ...] = (
    "Consumer Electronics",
    "Fast Moving Consumer Goods",
    "Education Services",
    "Healthcare",
    "Financial Services",
    "Hospitality",
    "E-commerce",
)

MIN_TARGET_RECORDS = 10000


@dataclass
class StateSeed:
    state: State
    base_x: float
    base_y: float
    size: float
    population: int
    area_km2: Decimal


def decimal_range(min_value: float, max_value: float, places: int = 2) -> Decimal:
    factor = 10**places
    raw = random.randint(int(min_value * factor), int(max_value * factor))
    return Decimal(raw) / Decimal(factor)


def create_polygon(x0: float, y0: float, width: float, height: float = None) -> MultiPolygon:
    height = height or width
    points = [
        (x0, y0),
        (x0 + width, y0),
        (x0 + width, y0 + height),
        (x0, y0 + height),
        (x0, y0),
    ]
    poly = Polygon(points, srid=4326)
    return MultiPolygon(poly, srid=4326)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


class Command(BaseCommand):
    help = "Generate a synthetic geospatial dataset with at least 10,000 records spanning all geo models."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--records",
            type=int,
            default=MIN_TARGET_RECORDS,
            help="Minimum number of demographic profile records to generate (default: 10000).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Purge existing geo records before generating new synthetic data.",
        )
        parser.add_argument(
            "--preserve-districts",
            action="store_true",
            help="Reuse existing district boundaries when available instead of regenerating synthetic grids.",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="",
            help="Target directory for exported CSV datasets (default: datasets/synthetic).",
        )

    def handle(self, *args, **options) -> None:
        target_records = max(options["records"], MIN_TARGET_RECORDS)
        output_dir = Path(options["output_dir"] or Path(settings.BASE_DIR) / "datasets" / "synthetic")
        ensure_directory(output_dir)

        if options["reset"]:
            self._reset_data()
        elif DemographicProfile.objects.count() >= target_records and District.objects.exists():
            self.stdout.write(self.style.SUCCESS("Synthetic geo dataset already meets the requested volume."))
            return

        state_seeds = self._create_states(options["preserve_districts"])
        districts, district_rows = self._create_districts(state_seeds, target_records, options["preserve_districts"])
        econ_rows = self._create_economic_indicators(districts)
        profile_rows = self._create_demographic_profiles(districts, target_records)
        industry_rows = self._create_industry_employment(districts)
        zone_rows = self._create_market_potential_zones(districts)

        self._export_csv(output_dir / "states.csv", self._state_headers(), [self._state_row(seed.state) for seed in state_seeds])
        self._export_csv(output_dir / "districts.csv", self._district_headers(), district_rows)
        self._export_csv(output_dir / "economic_indicators.csv", self._economic_headers(), econ_rows)
        self._export_csv(output_dir / "demographic_profiles.csv", self._demographic_headers(), profile_rows)
        self._export_csv(output_dir / "industry_employment.csv", self._industry_headers(), industry_rows)
        self._export_csv(output_dir / "market_potential_zones.csv", self._market_headers(), zone_rows)

        total_records = sum(len(series) for series in (district_rows, econ_rows, profile_rows, industry_rows, zone_rows)) + len(state_seeds)
        Dataset.objects.update_or_create(
            name="Synthetic GeoReach Dataset",
            defaults={
                "source": "generate_synthetic_geo_data management command",
                "feature_list": {
                    "state_fields": self._state_headers(),
                    "district_fields": self._district_headers(),
                    "economic_indicator_fields": self._economic_headers(),
                    "demographic_profile_fields": self._demographic_headers(),
                    "industry_employment_fields": self._industry_headers(),
                    "market_potential_fields": self._market_headers(),
                },
                "record_count": total_records,
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Synthetic dataset generated successfully with {len(profile_rows)} demographic profiles and {total_records} total records."
            )
        )

    def _reset_data(self) -> None:
        MarketPotentialZone.objects.all().delete()
        IndustryEmployment.objects.all().delete()
        EconomicIndicator.objects.all().delete()
        DemographicProfile.objects.all().delete()
        District.objects.all().delete()
        State.objects.all().delete()

    def _create_states(self, preserve_existing: bool) -> List[StateSeed]:
        seeds: List[StateSeed] = []
        
        # Try to load real state geometries from shapefile
        shapefile_dir = Path(settings.BASE_DIR) / 'datasets' / 'geodata'
        shapefile_path = shapefile_dir / 'india_states.shp'
        
        state_geometries = {}
        if shapefile_path.exists():
            self.stdout.write(self.style.SUCCESS(f"Loading state geometries from shapefile: {shapefile_path}"))
            gdf = gpd.read_file(shapefile_path)
            
            # Group by state name and merge geometries if there are duplicates
            for idx, row in gdf.iterrows():
                state_name = row.get('NAME_1') or row.get('name') or row.get('STATE')
                if not state_name:
                    continue
                
                # Normalize state name to match our database
                normalized_name = state_name.strip()
                if normalized_name == "Andaman and Nicobar":
                    normalized_name = "Andaman and Nicobar Islands"
                elif normalized_name == "NCT of Delhi" or normalized_name == "National Capital Territory of Delhi":
                    normalized_name = "Delhi"
                elif normalized_name == "Dadra and Nagar Haveli":
                    normalized_name = "Dadra and Nagar Haveli and Daman and Diu"
                elif normalized_name == "Daman and Diu":
                    continue  # Skip, will be merged with Dadra
                
                geom = row['geometry']
                if normalized_name in state_geometries:
                    # Merge with existing geometry (for states split across multiple rows)
                    from shapely.ops import unary_union
                    state_geometries[normalized_name] = unary_union([state_geometries[normalized_name], geom])
                else:
                    state_geometries[normalized_name] = geom
            
            self.stdout.write(self.style.SUCCESS(f"Loaded geometries for {len(state_geometries)} states"))
        
        # Create states with real or synthetic geometries
        columns = 9
        spacing = 2.5
        size = 1.2
        
        for index, (name, code) in enumerate(STATE_DATA):
            row = index // columns
            col = index % columns
            base_x = 65 + col * spacing
            base_y = 5 + row * spacing
            
            # Use real geometry from shapefile if available, otherwise synthetic
            if name in state_geometries:
                try:
                    geom_wkt = state_geometries[name].wkt
                    geometry = GEOSGeometry(geom_wkt, srid=4326)
                    
                    # Convert to MultiPolygon if it's a Polygon
                    if geometry.geom_type == 'Polygon':
                        geometry = MultiPolygon(geometry, srid=4326)
                    
                    centroid = geometry.centroid
                    
                    # Calculate area from real geometry
                    try:
                        geom_metric = geometry.transform(3857, clone=True)
                        area_km2 = Decimal(geom_metric.area / 1_000_000).quantize(Decimal("1.00"))
                    except:
                        area_km2 = decimal_range(4000, 200000)
                    
                    self.stdout.write(self.style.SUCCESS(f"Using real geometry for {name}"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error loading geometry for {name}: {e}, using synthetic"))
                    geometry = create_polygon(base_x, base_y, size)
                    centroid = geometry.centroid
                    centroid.srid = 4326
                    area_km2 = decimal_range(4000, 200000)
            else:
                # Fallback to synthetic geometry
                geometry = create_polygon(base_x, base_y, size)
                centroid = geometry.centroid
                centroid.srid = 4326
                area_km2 = decimal_range(4000, 200000)
            
            population = random.randint(3_000_000, 150_000_000)
            male_population = int(population * random.uniform(0.48, 0.52))
            female_population = population - male_population
            rural_population = int(population * random.uniform(0.35, 0.65))
            urban_population = population - rural_population
            density = (Decimal(population) / area_km2).quantize(Decimal("1.00"))

            state = State.objects.filter(name=name).first()
            if state is None:
                state = State.objects.create(
                    name=name,
                    code=code,
                    geometry=geometry,
                    centroid=centroid,
                    population=population,
                    male_population=male_population,
                    female_population=female_population,
                    sex_ratio=int((female_population / max(male_population, 1)) * 1000),
                    rural_population=rural_population,
                    urban_population=urban_population,
                    area_km2=area_km2,
                    population_density=density,
                )
            else:
                pending_updates: List[str] = []
                if state.code != code:
                    state.code = code
                    pending_updates.append("code")
                if not (preserve_existing and state.geometry):
                    state.geometry = geometry
                    state.centroid = centroid
                    pending_updates.extend(["geometry", "centroid"])
                else:
                    if state.centroid is None and state.geometry:
                        state.centroid = state.geometry.centroid
                        pending_updates.append("centroid")
                    geometry = state.geometry
                    centroid = state.centroid

                state.population = population
                state.male_population = male_population
                state.female_population = female_population
                state.sex_ratio = int((female_population / max(male_population, 1)) * 1000)
                state.rural_population = rural_population
                state.urban_population = urban_population
                state.area_km2 = area_km2
                state.population_density = density
                pending_updates.extend(
                    [
                        "population",
                        "male_population",
                        "female_population",
                        "sex_ratio",
                        "rural_population",
                        "urban_population",
                        "area_km2",
                        "population_density",
                    ]
                )
                state.save(update_fields=list(dict.fromkeys(pending_updates)))

            seeds.append(StateSeed(state=state, base_x=base_x, base_y=base_y, size=size, population=population, area_km2=area_km2))
        return seeds

    def _create_districts(
        self,
        state_seeds: Iterable[StateSeed],
        target_records: int,
        preserve_existing: bool,
    ) -> Tuple[List[District], List[Dict[str, str]]]:
        districts: List[District] = []
        district_rows: List[Dict[str, str]] = []
        combos = len(AGE_GROUPS) * len(EDUCATION_LEVELS)
        
        # Load real districts from shapefile
        shapefile_dir = Path(settings.BASE_DIR) / 'datasets' / 'geodata'
        shapefile_path = shapefile_dir / 'india_districts.shp'
        
        if shapefile_path.exists():
            self.stdout.write(self.style.SUCCESS(f"Loading districts from shapefile: {shapefile_path}"))
            gdf = gpd.read_file(shapefile_path)
            
            # Create state name mapping (handle variations)
            state_mapping = {seed.state.name: seed.state for seed in state_seeds}
            # Add common variations
            state_mapping["Andaman and Nicobar"] = state_mapping.get("Andaman and Nicobar Islands")
            state_mapping["Dadra and Nagar Haveli"] = state_mapping.get("Dadra and Nagar Haveli and Daman and Diu")
            state_mapping["Daman and Diu"] = state_mapping.get("Dadra and Nagar Haveli and Daman and Diu")
            state_mapping["NCT of Delhi"] = state_mapping.get("Delhi")
            state_mapping["National Capital Territory of Delhi"] = state_mapping.get("Delhi")
            
            for idx, row in gdf.iterrows():
                district_name = row.get('DISTRICT') or row.get('NAME_2') or row.get('name')
                state_name = row.get('STATE') or row.get('NAME_1') or row.get('state')
                
                if not district_name or not state_name:
                    continue
                
                # Map state name variations
                state = state_mapping.get(state_name)
                if not state:
                    # Try fuzzy match
                    for key, val in state_mapping.items():
                        if key and state_name and (key.lower() in state_name.lower() or state_name.lower() in key.lower()):
                            state = val
                            break
                
                if not state:
                    continue
                
                # Check if district already exists
                existing = District.objects.filter(name__iexact=district_name.strip(), state=state).first()
                if existing:
                    districts.append(existing)
                    continue
                
                # Convert geometry from shapefile to Django GEOS
                try:
                    geom_wkt = row['geometry'].wkt
                    geometry = GEOSGeometry(geom_wkt, srid=4326)
                    
                    # Convert to MultiPolygon if it's a Polygon
                    if geometry.geom_type == 'Polygon':
                        geometry = MultiPolygon(geometry, srid=4326)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not parse geometry for {district_name}: {e}"))
                    continue
                
                # Assign development tier for varied statistics
                tier_random = random.random()
                if tier_random < 0.15:
                    # Tier-1: High development
                    pop_range = (800_000, 5_000_000)
                    literacy_range = (78.0, 98.5)
                elif tier_random < 0.45:
                    # Tier-2: Upper-middle
                    pop_range = (300_000, 1_500_000)
                    literacy_range = (68.0, 85.0)
                elif tier_random < 0.80:
                    # Tier-3: Middle
                    pop_range = (150_000, 800_000)
                    literacy_range = (58.0, 75.0)
                else:
                    # Tier-4: Lower development
                    pop_range = (50_000, 400_000)
                    literacy_range = (45.0, 65.0)
                
                # Calculate area from geometry
                try:
                    geom_metric = geometry.transform(3857, clone=True)
                    area_sq_km = Decimal(geom_metric.area / 1_000_000).quantize(Decimal("1.00"))
                except:
                    area_sq_km = decimal_range(100, 5000)
                
                population = random.randint(pop_range[0], pop_range[1])
                
                district = District.objects.create(
                    name=district_name.strip(),
                    state=state,
                    geometry=geometry,
                    centroid=geometry.centroid,
                    population=population,
                    growth_rate=decimal_range(0.5, 6.5),
                    sex_ratio=random.randint(880, 1120),
                    literacy_rate=decimal_range(literacy_range[0], literacy_range[1]),
                    area_km2=area_sq_km,
                )
                districts.append(district)
                district_rows.append({
                    "state": state.name,
                    "state_code": state.code,
                    "district": district.name,
                    "population": str(population),
                    "growth_rate": str(district.growth_rate),
                    "sex_ratio": str(district.sex_ratio),
                    "literacy_rate": str(district.literacy_rate),
                    "area_km2": str(district.area_km2),
                    "geometry_wkt": district.geometry.wkt,
                })
            
            self.stdout.write(self.style.SUCCESS(f"Loaded {len(districts)} districts from shapefile"))
            return districts, district_rows
        
        # Fallback to synthetic district generation if shapefile not found
        self.stdout.write(self.style.WARNING(f"Shapefile not found, generating synthetic districts"))
        districts_per_state = max(math.ceil(target_records / (len(list(state_seeds)) * combos)), 6)

        for seed in state_seeds:
            existing_districts = list(District.objects.filter(state=seed.state))
            if preserve_existing and existing_districts:
                for district in existing_districts:
                    update_fields: List[str] = []
                    if not district.population or district.population <= 0:
                        district.population = random.randint(50_000, 8_000_000)
                        update_fields.append("population")
                    if district.growth_rate is None:
                        district.growth_rate = decimal_range(0.5, 6.5)
                        update_fields.append("growth_rate")
                    if district.sex_ratio is None:
                        district.sex_ratio = random.randint(880, 1120)
                        update_fields.append("sex_ratio")
                    if district.literacy_rate is None:
                        district.literacy_rate = decimal_range(58.0, 98.5)
                        update_fields.append("literacy_rate")
                    if (district.area_km2 is None or district.area_km2 == 0) and district.geometry:
                        try:
                            geom_metric = district.geometry.transform(3857, clone=True)
                            area_sq_km = Decimal(geom_metric.area / 1_000_000).quantize(Decimal("1.00"))
                            district.area_km2 = area_sq_km
                            update_fields.append("area_km2")
                        except Exception:  # pragma: no cover - transformation may fail if PROJ missing
                            pass
                    if district.centroid is None and district.geometry:
                        district.centroid = district.geometry.centroid
                        update_fields.append("centroid")
                    if update_fields:
                        district.save(update_fields=update_fields)
                    districts.append(district)
                    district_rows.append(
                        {
                            "state": seed.state.name,
                            "state_code": seed.state.code,
                            "district": district.name,
                            "population": str(district.population or ""),
                            "growth_rate": str(district.growth_rate or ""),
                            "sex_ratio": str(district.sex_ratio or ""),
                            "literacy_rate": str(district.literacy_rate or ""),
                            "area_km2": str(district.area_km2 or ""),
                            "geometry_wkt": district.geometry.wkt if district.geometry else "",
                        }
                    )
                continue

            District.objects.filter(state=seed.state).delete()
            grid_cols = math.ceil(math.sqrt(districts_per_state))
            cell_size = seed.size / grid_cols
            pop_weights = [random.uniform(0.5, 1.5) for _ in range(districts_per_state)]
            pop_total = sum(pop_weights)
            area_weights = [random.uniform(0.5, 1.5) for _ in range(districts_per_state)]
            area_total = sum(area_weights)
            rounded_populations = self._scaled_ints(pop_weights, pop_total, seed.population, minimum=35_000)
            rounded_areas = self._scaled_decimals(area_weights, area_total, seed.area_km2, minimum=Decimal("50.00"))

            for idx in range(districts_per_state):
                row = idx // grid_cols
                col = idx % grid_cols
                offset = cell_size * 0.1
                width = cell_size * 0.8
                geometry = create_polygon(seed.base_x + col * cell_size + offset, seed.base_y + row * cell_size + offset, width)
                centroid = geometry.centroid
                centroid.srid = 4326
                population = rounded_populations[idx]
                district = District.objects.create(
                    name=f"{seed.state.code}-D{idx + 1:02d}",
                    state=seed.state,
                    geometry=geometry,
                    centroid=centroid,
                    population=population,
                    growth_rate=decimal_range(0.5, 6.5),
                    sex_ratio=random.randint(880, 1120),
                    literacy_rate=decimal_range(58.0, 98.5),
                    area_km2=rounded_areas[idx],
                )
                districts.append(district)
                district_rows.append(
                    {
                        "state": seed.state.name,
                        "state_code": seed.state.code,
                        "district": district.name,
                        "population": str(population),
                        "growth_rate": str(district.growth_rate),
                        "sex_ratio": str(district.sex_ratio),
                        "literacy_rate": str(district.literacy_rate),
                        "area_km2": str(district.area_km2),
                        "geometry_wkt": district.geometry.wkt,
                    }
                )
        return districts, district_rows

    def _create_economic_indicators(self, districts: Iterable[District]) -> List[Dict[str, str]]:
        indicators: List[EconomicIndicator] = []
        rows: List[Dict[str, str]] = []
        
        # Create district tiers for varied economic profiles  
        district_list = list(districts)
        random.shuffle(district_list)
        
        tier1_count = int(len(district_list) * 0.15)
        tier2_count = int(len(district_list) * 0.30)
        tier3_count = int(len(district_list) * 0.35)
        
        tier1_districts = set(district_list[:tier1_count])
        tier2_districts = set(district_list[tier1_count:tier1_count + tier2_count])
        tier3_districts = set(district_list[tier1_count + tier2_count:tier1_count + tier2_count + tier3_count])
        
        for district in districts:
            # Determine tier-based characteristics
            if district in tier1_districts:
                # Tier-1: Prefer urban, lower unemployment, higher salaries
                area_weights = {'URBAN': 5, 'COMBINED': 2, 'RURAL': 1}
                unemployment_range = (2.0, 6.0)
                salary_range = (60_000, 120_000)
            elif district in tier2_districts:
                # Tier-2: Mixed areas, moderate stats
                area_weights = {'URBAN': 3, 'COMBINED': 4, 'RURAL': 2}
                unemployment_range = (4.0, 8.5)
                salary_range = (35_000, 75_000)
            elif district in tier3_districts:
                # Tier-3: More rural, higher unemployment
                area_weights = {'URBAN': 2, 'COMBINED': 3, 'RURAL': 4}
                unemployment_range = (6.0, 10.5)
                salary_range = (20_000, 50_000)
            else:
                # Tier-4: Predominantly rural, high unemployment, low salaries
                area_weights = {'URBAN': 1, 'COMBINED': 2, 'RURAL': 5}
                unemployment_range = (8.0, 12.5)
                salary_range = (8_000, 35_000)
            
            # Weighted random selection of area types
            area_choices = []
            for area_type in AREA_TYPES:
                weight = area_weights.get(area_type, 1)
                area_choices.extend([area_type] * weight)
            
            for area_type in AREA_TYPES:
                # Use weighted probability for this district's primary area type
                if area_type == random.choice(area_choices):
                    year = random.randint(2023, 2024)  # Recent data
                    month = random.choice([1, 7])  # Jan or July
                    unemployment_rate = decimal_range(unemployment_range[0], unemployment_range[1])
                else:
                    # Other area types get slightly different stats
                    year = random.randint(2022, 2024)
                    month = random.randint(1, 12)
                    unemployment_rate = decimal_range(2.0, 12.5)
                
                employment_rate = (Decimal("100.00") - unemployment_rate + decimal_range(-1.5, 1.5)).quantize(Decimal("1.00"))
                employment_rate = max(Decimal("35.00"), min(employment_rate, Decimal("100.00")))
                estimated_employed = int(district.population * float(employment_rate) / 100)
                
                # Salary based on tier
                avg_salary = decimal_range(salary_range[0], salary_range[1])
                
                # Salary based on tier
                avg_salary = decimal_range(salary_range[0], salary_range[1])
                
                record = EconomicIndicator(
                    state=district.state,
                    district=district,
                    year=year,
                    month=month,
                    date_recorded=date(year, month, 1),
                    area_type=area_type,
                    unemployment_rate=unemployment_rate,
                    employment_rate=employment_rate,
                    estimated_employed=estimated_employed,
                    labour_participation_rate=decimal_range(40.0, 75.0),
                    avg_monthly_salary=avg_salary,
                )
                indicators.append(record)
                rows.append(
                    {
                        "state": district.state.name,
                        "district": district.name,
                        "area_type": area_type,
                        "year": str(year),
                        "month": str(month),
                        "unemployment_rate": str(unemployment_rate),
                        "employment_rate": str(employment_rate),
                        "estimated_employed": str(estimated_employed),
                        "labour_participation_rate": str(record.labour_participation_rate),
                        "avg_monthly_salary": str(record.avg_monthly_salary),
                    }
                )
        EconomicIndicator.objects.bulk_create(indicators, batch_size=1000)
        return rows

    def _create_demographic_profiles(self, districts: Iterable[District], target_records: int) -> List[Dict[str, str]]:
        profiles: List[DemographicProfile] = []
        rows: List[Dict[str, str]] = []
        
        # Create district development tiers for varied distribution (better visual results)
        district_list = list(districts)
        random.shuffle(district_list)
        
        # Tier distribution: 15% Tier-1, 30% Tier-2, 35% Tier-3, 20% Tier-4
        tier1_count = int(len(district_list) * 0.15)
        tier2_count = int(len(district_list) * 0.30)
        tier3_count = int(len(district_list) * 0.35)
        
        tier1_districts = set(district_list[:tier1_count])
        tier2_districts = set(district_list[tier1_count:tier1_count + tier2_count])
        tier3_districts = set(district_list[tier1_count + tier2_count:tier1_count + tier2_count + tier3_count])
        # tier4_districts are the rest
        
        for district in districts:
            # Determine district tier and set income/expenditure ranges accordingly
            if district in tier1_districts:
                # Tier-1: High development (metro cities)
                income_range = (80_000, 180_000)
                literacy_boost = 1.15
                urban_probability = 0.8
            elif district in tier2_districts:
                # Tier-2: Upper-middle development
                income_range = (50_000, 100_000)
                literacy_boost = 1.05
                urban_probability = 0.5
            elif district in tier3_districts:
                # Tier-3: Middle development
                income_range = (30_000, 65_000)
                literacy_boost = 0.95
                urban_probability = 0.3
            else:
                # Tier-4: Lower development (rural)
                income_range = (15_000, 45_000)
                literacy_boost = 0.85
                urban_probability = 0.1
            
            for age_group in AGE_GROUPS:
                for education in EDUCATION_LEVELS:
                    # Education level affects income
                    education_multiplier = {
                        'Below High School': 0.6,
                        'High School': 0.8,
                        'Some College': 1.0,
                        'Bachelor': 1.3,
                        'Master': 1.6,
                        'PhD': 1.8,
                    }.get(education, 1.0)
                    
                    base_income = decimal_range(income_range[0], income_range[1])
                    income = base_income * Decimal(str(education_multiplier))
                    
                    # Disposable income (after taxes/savings) - 40-70% of income
                    disposable_ratio = random.uniform(0.40, 0.70)
                    disposable = income * Decimal(str(disposable_ratio))
                    
                    # Expenditures as proportion of disposable income (varied by tier)
                    if income > 80000:
                        # High income: Lower food %, higher discretionary %
                        groceries = disposable * Decimal(str(random.uniform(0.08, 0.15)))
                        eating_out = disposable * Decimal(str(random.uniform(0.05, 0.12)))
                        entertainment = disposable * Decimal(str(random.uniform(0.04, 0.10)))
                        healthcare = disposable * Decimal(str(random.uniform(0.03, 0.08)))
                        education_spend = disposable * Decimal(str(random.uniform(0.05, 0.12)))
                    elif income > 50000:
                        # Middle-high income
                        groceries = disposable * Decimal(str(random.uniform(0.12, 0.22)))
                        eating_out = disposable * Decimal(str(random.uniform(0.03, 0.08)))
                        entertainment = disposable * Decimal(str(random.uniform(0.02, 0.06)))
                        healthcare = disposable * Decimal(str(random.uniform(0.02, 0.06)))
                        education_spend = disposable * Decimal(str(random.uniform(0.03, 0.08)))
                    elif income > 30000:
                        # Middle income
                        groceries = disposable * Decimal(str(random.uniform(0.18, 0.30)))
                        eating_out = disposable * Decimal(str(random.uniform(0.02, 0.05)))
                        entertainment = disposable * Decimal(str(random.uniform(0.01, 0.04)))
                        healthcare = disposable * Decimal(str(random.uniform(0.02, 0.05)))
                        education_spend = disposable * Decimal(str(random.uniform(0.02, 0.06)))
                    else:
                        # Low income: High food %, minimal discretionary
                        groceries = disposable * Decimal(str(random.uniform(0.25, 0.40)))
                        eating_out = disposable * Decimal(str(random.uniform(0.01, 0.03)))
                        entertainment = disposable * Decimal(str(random.uniform(0.005, 0.02)))
                        healthcare = disposable * Decimal(str(random.uniform(0.015, 0.04)))
                        education_spend = disposable * Decimal(str(random.uniform(0.01, 0.03)))
                    
                    transport = disposable * Decimal(str(random.uniform(0.05, 0.15)))
                    utilities = disposable * Decimal(str(random.uniform(0.08, 0.18)))
                    transport = disposable * Decimal(str(random.uniform(0.05, 0.15)))
                    utilities = disposable * Decimal(str(random.uniform(0.08, 0.18)))
                    
                    avg_spending = sum([groceries, transport, eating_out, entertainment, utilities, healthcare, education_spend])
                    
                    profile = DemographicProfile(
                        state=district.state,
                        district=district,
                        age_group=age_group,
                        education_level=education,
                        occupation=random.choice(OCCUPATIONS),
                        avg_income=income,
                        avg_disposable_income=disposable,
                        groceries_expenditure=groceries,
                        transport_expenditure=transport,
                        eating_out_expenditure=eating_out,
                        entertainment_expenditure=entertainment,
                        utilities_expenditure=utilities,
                        healthcare_expenditure=healthcare,
                        education_expenditure=education_spend,
                        avg_purchase_frequency=decimal_range(1.0, 24.0),
                        avg_spending=avg_spending,
                        sample_size=random.randint(250, 5500),
                    )
                    profiles.append(profile)
                    rows.append(
                        {
                            "state": district.state.name,
                            "district": district.name,
                            "age_group": age_group,
                            "education_level": education,
                            "occupation": profile.occupation or "",
                            "avg_income": str(income),
                            "avg_disposable_income": str(disposable),
                            "avg_spending": str(avg_spending),
                            "avg_purchase_frequency": str(profile.avg_purchase_frequency),
                            "sample_size": str(profile.sample_size),
                            "groceries_expenditure": str(groceries),
                            "transport_expenditure": str(transport),
                            "eating_out_expenditure": str(eating_out),
                            "entertainment_expenditure": str(entertainment),
                            "utilities_expenditure": str(utilities),
                            "healthcare_expenditure": str(healthcare),
                            "education_expenditure": str(education_spend),
                        }
                    )
        DemographicProfile.objects.bulk_create(profiles, batch_size=1000)
        return rows

    def _create_industry_employment(self, districts: Iterable[District]) -> List[Dict[str, str]]:
        records: List[IndustryEmployment] = []
        rows: List[Dict[str, str]] = []
        for district in districts:
            industries = random.sample(INDUSTRIES, k=min(3, len(INDUSTRIES)))
            for industry in industries:
                employed = random.randint(max(500, district.population // 150), max(1200, district.population // 12))
                unemployed = random.randint(100, max(300, employed // 3))
                avg_salary = decimal_range(7_000, 140_000)
                record = IndustryEmployment(
                    state=district.state,
                    district=district,
                    industry=industry,
                    employed_count=employed,
                    unemployed_count=unemployed,
                    avg_salary=avg_salary,
                    date_recorded=date(random.randint(2019, 2025), random.randint(1, 12), 1),
                )
                records.append(record)
                rows.append(
                    {
                        "state": district.state.name,
                        "district": district.name,
                        "industry": industry,
                        "employed_count": str(employed),
                        "unemployed_count": str(unemployed),
                        "avg_salary": str(avg_salary),
                        "date_recorded": record.date_recorded.isoformat(),
                    }
                )
        IndustryEmployment.objects.bulk_create(records, batch_size=1000)
        return rows

    def _create_market_potential_zones(self, districts: Iterable[District]) -> List[Dict[str, str]]:
        records: List[MarketPotentialZone] = []
        rows: List[Dict[str, str]] = []
        for district in districts:
            potential_level = random.choice(POTENTIAL_LEVELS)
            market_score = decimal_range(45.0, 97.5)
            reach_percentage = decimal_range(5.0, 85.0)
            target_population = int(district.population * random.uniform(0.05, 0.55))
            record = MarketPotentialZone(
                state=district.state,
                district=district,
                product_type=random.choice(PRODUCT_TYPES),
                product_category=random.choice(["Premium", "Standard", "Value"]),
                target_age_group=random.choice(AGE_GROUPS),
                target_income_range=random.choice(["<5L", "5L-10L", "10L-20L", ">20L"]),
                potential_level=potential_level,
                market_score=market_score,
                predicted_reach_percentage=reach_percentage,
                estimated_target_population=target_population,
                zone_geometry=district.geometry,
            )
            records.append(record)
            rows.append(
                {
                    "state": district.state.name,
                    "district": district.name,
                    "product_type": record.product_type,
                    "product_category": record.product_category or "",
                    "target_age_group": record.target_age_group or "",
                    "target_income_range": record.target_income_range or "",
                    "potential_level": potential_level,
                    "market_score": str(market_score),
                    "predicted_reach_percentage": str(reach_percentage),
                    "estimated_target_population": str(target_population),
                }
            )
        MarketPotentialZone.objects.bulk_create(records, batch_size=1000)
        return rows

    def _export_csv(self, path: Path, headers: Iterable[str], rows: Iterable[Dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(headers))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _state_headers() -> List[str]:
        return [
            "name",
            "code",
            "population",
            "male_population",
            "female_population",
            "rural_population",
            "urban_population",
            "sex_ratio",
            "area_km2",
            "population_density",
            "centroid_lon",
            "centroid_lat",
        ]

    @staticmethod
    def _state_row(state: State) -> Dict[str, str]:
        centroid: Point = state.centroid
        return {
            "name": state.name,
            "code": state.code or "",
            "population": str(state.population or 0),
            "male_population": str(state.male_population or 0),
            "female_population": str(state.female_population or 0),
            "rural_population": str(state.rural_population or 0),
            "urban_population": str(state.urban_population or 0),
            "sex_ratio": str(state.sex_ratio or 0),
            "area_km2": str(state.area_km2 or "0"),
            "population_density": str(state.population_density or "0"),
            "centroid_lon": f"{centroid.x:.6f}" if centroid else "",
            "centroid_lat": f"{centroid.y:.6f}" if centroid else "",
        }

    @staticmethod
    def _district_headers() -> List[str]:
        return [
            "state",
            "state_code",
            "district",
            "population",
            "growth_rate",
            "sex_ratio",
            "literacy_rate",
            "area_km2",
            "geometry_wkt",
        ]

    @staticmethod
    def _economic_headers() -> List[str]:
        return [
            "state",
            "district",
            "area_type",
            "year",
            "month",
            "unemployment_rate",
            "employment_rate",
            "estimated_employed",
            "labour_participation_rate",
            "avg_monthly_salary",
        ]

    @staticmethod
    def _demographic_headers() -> List[str]:
        return [
            "state",
            "district",
            "age_group",
            "education_level",
            "occupation",
            "avg_income",
            "avg_disposable_income",
            "avg_spending",
            "avg_purchase_frequency",
            "sample_size",
            "groceries_expenditure",
            "transport_expenditure",
            "eating_out_expenditure",
            "entertainment_expenditure",
            "utilities_expenditure",
            "healthcare_expenditure",
            "education_expenditure",
        ]

    @staticmethod
    def _industry_headers() -> List[str]:
        return [
            "state",
            "district",
            "industry",
            "employed_count",
            "unemployed_count",
            "avg_salary",
            "date_recorded",
        ]

    @staticmethod
    def _market_headers() -> List[str]:
        return [
            "state",
            "district",
            "product_type",
            "product_category",
            "target_age_group",
            "target_income_range",
            "potential_level",
            "market_score",
            "predicted_reach_percentage",
            "estimated_target_population",
        ]

    @staticmethod
    def _scaled_ints(weights: List[float], total_weight: float, target_sum: int, minimum: int) -> List[int]:
        raw = [target_sum * w / total_weight for w in weights]
        rounded = [max(minimum, int(value)) for value in raw]
        diff = target_sum - sum(rounded)
        idx = 0
        while diff != 0 and idx < len(rounded) * 3:
            pointer = idx % len(rounded)
            if diff > 0:
                rounded[pointer] += 1
                diff -= 1
            elif rounded[pointer] > minimum:
                rounded[pointer] -= 1
                diff += 1
            idx += 1
        return rounded

    @staticmethod
    def _scaled_decimals(weights: List[float], total_weight: float, target_sum: Decimal, minimum: Decimal) -> List[Decimal]:
        raw = [target_sum * Decimal(w) / Decimal(total_weight) for w in weights]
        rounded = [max(minimum, value.quantize(Decimal("1.00"))) for value in raw]
        diff = target_sum - sum(rounded)
        step = Decimal("0.01")
        idx = 0
        while diff.copy_abs() >= step and idx < len(rounded) * 3:
            pointer = idx % len(rounded)
            if diff > 0:
                rounded[pointer] += step
                diff -= step
            elif rounded[pointer] - step >= minimum:
                rounded[pointer] -= step
                diff += step
            idx += 1
        return rounded
