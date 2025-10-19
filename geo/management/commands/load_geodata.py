from django.core.management.base import BaseCommand
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.geos import GEOSGeometry, Point
from django.db import transaction
from geo.models import State, District, EconomicIndicator, DemographicProfile, IndustryEmployment
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import re


class Command(BaseCommand):
    help = 'Load geographic and demographic data into PostGIS database'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-shapefiles',
            action='store_true',
            help='Skip loading shapefiles',
        )
        parser.add_argument(
            '--skip-demographics',
            action='store_true',
            help='Skip loading demographic data',
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing data before loading',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting geodata import..."))
        
        # Get the base directory
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        
        if options['clear_existing']:
            self.stdout.write(self.style.WARNING("Clearing existing data..."))
            self.clear_data()
        
        # Load shapefiles
        if not options['skip_shapefiles']:
            self.load_states(base_dir)
            self.load_districts(base_dir)
        
        # Load CSV data
        if not options['skip_demographics']:
            self.load_population_data(base_dir)
            self.load_employment_data(base_dir)
            self.load_demographic_profiles(base_dir)
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded all geodata!'))
    
    def clear_data(self):
        """Clear existing data"""
        DemographicProfile.objects.all().delete()
        IndustryEmployment.objects.all().delete()
        EconomicIndicator.objects.all().delete()
        District.objects.all().delete()
        State.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared existing data'))
    
    def load_states(self, base_dir):
        """Load state boundaries from shapefile"""
        self.stdout.write("Loading states...")
        
        shapefile_path = base_dir / 'datasets' / 'geodata' / 'india_states.shp'
        
        if not shapefile_path.exists():
            self.stdout.write(self.style.WARNING(f'Shapefile not found: {shapefile_path}'))
            self.create_sample_states()
            return
        
        try:
            # Read shapefile attributes to determine field mapping
            from django.contrib.gis.gdal import DataSource
            ds = DataSource(str(shapefile_path))
            layer = ds[0]
            
            self.stdout.write(f"Shapefile fields: {layer.fields}")
            
            # Adjust mapping based on actual fields
            # Common field names: shapeName, NAME, ST_NM, State_Name, etc.
            state_mapping = {
                'geometry': 'MULTIPOLYGON',
            }
            
            # Try to find name field
            for field in layer.fields:
                if any(x in field.lower() for x in ['name', 'st_nm', 'state']):
                    state_mapping['name'] = field
                    break
            
            if 'name' not in state_mapping:
                self.stdout.write(self.style.ERROR('Could not find name field in shapefile'))
                return
            
            # Import using LayerMapping
            lm = LayerMapping(
                State, 
                str(shapefile_path), 
                state_mapping,
                transform=False,
                encoding='utf-8'
            )
            lm.save(strict=True, verbose=False)
            
            self.stdout.write(self.style.SUCCESS(f'Loaded {State.objects.count()} states'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading states: {e}'))
            self.create_sample_states()
    
    def create_sample_states(self):
        """Create sample states for testing"""
        self.stdout.write("Creating sample states...")
        
        # Create simple polygon geometries for testing
        from django.contrib.gis.geos import Polygon, MultiPolygon
        
        sample_states = [
            {
                'name': 'Maharashtra',
                'code': 'MH',
                'coords': ((72.0, 15.0), (78.0, 15.0), (78.0, 22.0), (72.0, 22.0), (72.0, 15.0))
            },
            {
                'name': 'Delhi',
                'code': 'DL',
                'coords': ((76.8, 28.4), (77.3, 28.4), (77.3, 28.9), (76.8, 28.9), (76.8, 28.4))
            },
            {
                'name': 'Karnataka',
                'code': 'KA',
                'coords': ((74.0, 11.5), (78.5, 11.5), (78.5, 18.5), (74.0, 18.5), (74.0, 11.5))
            },
        ]
        
        for state_data in sample_states:
            polygon = Polygon(state_data['coords'])
            multi_polygon = MultiPolygon(polygon)
            
            State.objects.get_or_create(
                name=state_data['name'],
                defaults={
                    'code': state_data['code'],
                    'geometry': multi_polygon
                }
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {State.objects.count()} sample states'))
    
    def load_districts(self, base_dir):
        """Load district boundaries from shapefile"""
        self.stdout.write("Loading districts...")
        
        shapefile_path = base_dir / 'datasets' / 'geodata' / 'india_districts.shp'
        
        if not shapefile_path.exists():
            self.stdout.write(self.style.WARNING(f'Shapefile not found: {shapefile_path}'))
            self.create_sample_districts()
            return
        
        try:
            from django.contrib.gis.gdal import DataSource
            ds = DataSource(str(shapefile_path))
            layer = ds[0]
            
            self.stdout.write(f"District shapefile fields: {layer.fields}")
            
            # Import districts
            for feature in layer:
                district_name = None
                state_name = None
                
                # Find name fields
                for field in layer.fields:
                    if any(x in field.lower() for x in ['dist', 'district']):
                        district_name = feature.get(field)
                    if any(x in field.lower() for x in ['state', 'st_nm']):
                        state_name = feature.get(field)
                
                if not district_name:
                    continue
                
                # Find or create state
                state = None
                if state_name:
                    state = State.objects.filter(name__icontains=state_name).first()
                
                if not state:
                    # Find state by spatial containment
                    geom = feature.geom.geos
                    state = State.objects.filter(geometry__contains=geom.centroid).first()
                
                if state:
                    District.objects.get_or_create(
                        name=district_name,
                        state=state,
                        defaults={'geometry': geom}
                    )
            
            self.link_districts_to_states()
            self.stdout.write(self.style.SUCCESS(f'Loaded {District.objects.count()} districts'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading districts: {e}'))
            self.create_sample_districts()
    
    def create_sample_districts(self):
        """Create sample districts for testing"""
        self.stdout.write("Creating sample districts...")
        
        from django.contrib.gis.geos import Polygon, MultiPolygon
        
        # Get existing states
        maharashtra = State.objects.filter(name='Maharashtra').first()
        delhi = State.objects.filter(name='Delhi').first()
        karnataka = State.objects.filter(name='Karnataka').first()
        
        sample_districts = []
        
        if maharashtra:
            sample_districts.append({
                'name': 'Mumbai',
                'state': maharashtra,
                'coords': ((72.7, 18.9), (72.9, 18.9), (72.9, 19.3), (72.7, 19.3), (72.7, 18.9))
            })
            sample_districts.append({
                'name': 'Pune',
                'state': maharashtra,
                'coords': ((73.6, 18.4), (74.0, 18.4), (74.0, 18.7), (73.6, 18.7), (73.6, 18.4))
            })
        
        if delhi:
            sample_districts.append({
                'name': 'Central Delhi',
                'state': delhi,
                'coords': ((77.1, 28.6), (77.3, 28.6), (77.3, 28.7), (77.1, 28.7), (77.1, 28.6))
            })
        
        if karnataka:
            sample_districts.append({
                'name': 'Bangalore Urban',
                'state': karnataka,
                'coords': ((77.4, 12.8), (77.8, 12.8), (77.8, 13.2), (77.4, 13.2), (77.4, 12.8))
            })
        
        for district_data in sample_districts:
            polygon = Polygon(district_data['coords'])
            multi_polygon = MultiPolygon(polygon)
            
            District.objects.get_or_create(
                name=district_data['name'],
                state=district_data['state'],
                defaults={'geometry': multi_polygon}
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {District.objects.count()} sample districts'))
    
    def link_districts_to_states(self):
        """Link districts to states based on spatial containment"""
        self.stdout.write("Linking districts to states...")
        
        districts_without_state = District.objects.filter(state__isnull=True)
        
        for district in districts_without_state:
            # Find which state contains this district
            states = State.objects.filter(geometry__contains=district.centroid)
            if states.exists():
                district.state = states.first()
                district.save()
    
    def load_population_data(self, base_dir):
        """Load population data from CSV"""
        self.stdout.write("Loading population data...")
        
        csv_path = base_dir / 'datasets' / 'India_Districts_Population.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f'CSV not found: {csv_path}'))
            return
        
        try:
            df = pd.read_csv(csv_path)
            
            for _, row in df.iterrows():
                try:
                    # Clean population value
                    pop_str = str(row['Population']).replace(',', '').strip()
                    population = int(pop_str) if pop_str.isdigit() else None
                    
                    # Clean literacy rate
                    literacy_str = str(row['Literacy']).replace('%', '').strip()
                    literacy = float(literacy_str) if literacy_str.replace('.', '').isdigit() else None
                    
                    # Clean growth rate
                    growth_str = str(row['Growth']).replace('%', '').strip()
                    growth = float(growth_str) if growth_str.replace('.', '').replace('-', '').isdigit() else None
                    
                    # Clean sex ratio
                    sex_ratio_str = str(row['Sex-Ratio']).strip()
                    sex_ratio = int(sex_ratio_str) if sex_ratio_str.isdigit() else None
                    
                    # Find district
                    district = District.objects.filter(name__iexact=row['District']).first()
                    
                    if district:
                        district.population = population
                        district.literacy_rate = literacy
                        district.growth_rate = growth
                        district.sex_ratio = sex_ratio
                        district.save()
                        
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Error processing {row.get('District', 'unknown')}: {e}"))
                    continue
            
            self.stdout.write(self.style.SUCCESS('Population data loaded'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading population data: {e}'))
    
    def load_employment_data(self, base_dir):
        """Load employment data from geodata/dataset5.csv"""
        self.stdout.write("Loading employment data...")
        
        csv_path = base_dir / 'datasets' / 'geodata' / 'dataset5.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f'CSV not found: {csv_path}'))
            return
        
        try:
            df = pd.read_csv(csv_path)
            
            # Map locations to states
            location_state_map = {
                'Delhi': 'Delhi',
                'Urban': None,  # Will skip
                'Mumbai': 'Maharashtra',
                'Bangalore': 'Karnataka',
                'Kolkata': 'West Bengal',
                'Chennai': 'Tamil Nadu',
                'Hyderabad': 'Telangana',
            }
            
            # Group by location and industry
            for location in df['Location'].unique():
                state_name = location_state_map.get(location)
                
                if not state_name:
                    continue
                
                state = State.objects.filter(name__icontains=state_name).first()
                
                if state:
                    for industry in df['Industry'].unique():
                        subset = df[(df['Location'] == location) & (df['Industry'] == industry)]
                        
                        employed = subset[subset['Employment_Status'] == 'Employed']
                        unemployed = subset[subset['Employment_Status'] == 'Unemployed']
                        
                        # Map industry name to choices
                        industry_mapped = industry.upper()
                        if industry_mapped not in dict(IndustryEmployment.INDUSTRY_CHOICES):
                            industry_mapped = 'OTHER'
                        
                        IndustryEmployment.objects.get_or_create(
                            state=state,
                            industry=industry_mapped,
                            defaults={
                                'employed_count': len(employed),
                                'unemployed_count': len(unemployed),
                                'avg_salary': employed['Monthly_Salary_INR'].mean() if len(employed) > 0 else None,
                                'date_recorded': datetime.now().date()
                            }
                        )
            
            self.stdout.write(self.style.SUCCESS('Employment data loaded'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading employment data: {e}'))
    
    def load_demographic_profiles(self, base_dir):
        """Load demographic spending profiles"""
        self.stdout.write("Loading demographic profiles...")
        
        csv_path = base_dir / 'datasets' / 'geodata' / 'dataset3.csv'
        
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f'CSV not found: {csv_path}'))
            return
        
        try:
            df = pd.read_csv(csv_path)
            
            # Map age ranges
            def get_age_group(age):
                if age < 25:
                    return '18-24'
                elif age < 35:
                    return '25-34'
                elif age < 45:
                    return '35-44'
                elif age < 55:
                    return '45-54'
                else:
                    return '55+'
            
            df['age_group'] = df['Age'].apply(get_age_group)
            
            # Get all states
            states = State.objects.all()
            
            if not states.exists():
                self.stdout.write(self.style.WARNING('No states found. Skipping demographic profiles.'))
                return
            
            # Group by city tier and age group
            for city_tier in df['City_Tier'].unique():
                for age_group in df['age_group'].unique():
                    subset = df[(df['City_Tier'] == city_tier) & (df['age_group'] == age_group)]
                    
                    if len(subset) > 0:
                        # Create profile for a sample state (you can enhance this logic)
                        for state in states[:3]:  # Limit to first 3 states for demo
                            DemographicProfile.objects.get_or_create(
                                state=state,
                                age_group=age_group,
                                city_tier=city_tier.upper(),
                                defaults={
                                    'avg_income': subset['Income'].mean(),
                                    'avg_disposable_income': subset['Disposable_Income'].mean(),
                                    'groceries_expenditure': subset['Groceries_Expenditure'].mean(),
                                    'transport_expenditure': subset['Transport_Expenditure'].mean(),
                                    'eating_out_expenditure': subset['Eating_Out_Expenditure'].mean(),
                                    'entertainment_expenditure': subset['Entertainment_Expenditure'].mean(),
                                    'utilities_expenditure': subset['Utilities_Expenditure'].mean(),
                                    'healthcare_expenditure': subset['Healthcare_Expenditure'].mean(),
                                    'education_expenditure': subset['Education_Expenditure'].mean(),
                                    'sample_size': len(subset)
                                }
                            )
            
            self.stdout.write(self.style.SUCCESS('Demographic profiles loaded'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading demographic profiles: {e}'))
