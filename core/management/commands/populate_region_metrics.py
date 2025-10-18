from django.core.management.base import BaseCommand
from django.db import connection
from core.models import RegionMetrics
import json

class Command(BaseCommand):
    help = 'Populate region_metrics table with precomputed data'

    def handle(self, *args, **options):
        self.stdout.write('Populating region_metrics...')
        
        # 1. Populate state metrics
        self.populate_state_metrics()
        
        # 2. Populate district metrics
        self.populate_district_metrics()
        
        self.stdout.write(self.style.SUCCESS('✅ Region metrics populated successfully!'))

    def populate_state_metrics(self):
        """Populate metrics for all states"""
        query = """
            SELECT 
                s.state_id,
                s.state_name,
                s.population,
                s.population_density,
                s.est_unemployment_rate,
                s.est_employed,
                s.area_type,
                ROUND((s.est_employed::numeric / NULLIF(s.population, 0)::numeric * 100), 2) as employment_rate,
                c.avg_income,
                c.avg_spending
            FROM states s
            LEFT JOIN (
                SELECT 
                    location,
                    AVG(income) as avg_income,
                    AVG(spending) as avg_spending
                FROM customers
                WHERE location IS NOT NULL
                GROUP BY location
            ) c ON s.state_name = c.location
            WHERE s.state_name IS NOT NULL
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                
                # Calculate spending index if data available
                spending_index = None
                if data.get('avg_income') and data.get('avg_spending'):
                    spending_index = float(data['avg_spending']) / float(data['avg_income']) if float(data['avg_income']) > 0 else None
                
                RegionMetrics.objects.update_or_create(
                    region_type='state',
                    region_id=data['state_id'],
                    defaults={
                        'region_name': data['state_name'],
                        'population_density': data.get('population_density'),
                        'employment_rate': data.get('employment_rate'),
                        'avg_income': data.get('avg_income'),
                        'avg_spending': data.get('avg_spending'),
                        'spending_index': spending_index,
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('✅ State metrics populated'))

    def populate_district_metrics(self):
        """Populate metrics for all districts"""
        query = """
            SELECT 
                d.district_id,
                d.district_name,
                s.state_name,
                d.population_district,
                d.literacy_rate,
                s.population_density,
                ROUND((s.est_employed::numeric / NULLIF(s.population, 0)::numeric * 100), 2) as employment_rate,
                s.area_type
            FROM districts d
            LEFT JOIN states s ON d.state_id = s.state_id
            WHERE d.district_name IS NOT NULL
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            
            for row in cursor.fetchall():
                data = dict(zip(columns, row))
                
                RegionMetrics.objects.update_or_create(
                    region_type='district',
                    region_id=data['district_id'],
                    defaults={
                        'region_name': data['district_name'],
                        'population_density': data.get('population_density'),
                        'literacy_rate': data.get('literacy_rate'),
                        'employment_rate': data.get('employment_rate'),
                    }
                )
        
        self.stdout.write(self.style.SUCCESS('✅ District metrics populated'))