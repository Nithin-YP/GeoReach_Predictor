import csv
import math
import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from django.conf import settings
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
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
    ("Ladakh", "LA"),
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
        columns = 9
        spacing = 2.5
        size = 1.2
        for index, (name, code) in enumerate(STATE_DATA):
            row = index // columns
            col = index % columns
            base_x = 65 + col * spacing
            base_y = 5 + row * spacing
            geometry = create_polygon(base_x, base_y, size)
            centroid = geometry.centroid
            centroid.srid = 4326
            population = random.randint(3_000_000, 150_000_000)
            male_population = int(population * random.uniform(0.48, 0.52))
            female_population = population - male_population
            rural_population = int(population * random.uniform(0.35, 0.65))
            urban_population = population - rural_population
            area_km2 = decimal_range(4000, 200000)
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
        districts_per_state = max(math.ceil(target_records / (len(state_seeds) * combos)), 6)

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
        for district in districts:
            for area_type in AREA_TYPES:
                year = random.randint(2019, 2025)
                month = random.randint(1, 12)
                unemployment_rate = decimal_range(2.0, 12.5)
                employment_rate = (Decimal("100.00") - unemployment_rate + decimal_range(-1.5, 1.5)).quantize(Decimal("1.00"))
                employment_rate = max(Decimal("35.00"), min(employment_rate, Decimal("100.00")))
                estimated_employed = int(district.population * float(employment_rate) / 100)
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
                    avg_monthly_salary=decimal_range(8_000, 120_000),
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
        for district in districts:
            for age_group in AGE_GROUPS:
                for education in EDUCATION_LEVELS:
                    income = decimal_range(25_000, 180_000)
                    disposable = max(Decimal("0.00"), income - decimal_range(5_000, 70_000))
                    groceries = decimal_range(2_000, 25_000)
                    transport = decimal_range(1_000, 12_000)
                    eating_out = decimal_range(800, 10_000)
                    entertainment = decimal_range(500, 8_000)
                    utilities = decimal_range(1_500, 9_000)
                    healthcare = decimal_range(600, 12_000)
                    education_spend = decimal_range(800, 10_000)
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
