from django.contrib.gis.db import models as gis_models
from django.db import models
from django.contrib.gis.geos import Point, MultiPolygon


class State(gis_models.Model):
    """Indian States with geometric boundaries"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True, null=True, blank=True)  # e.g., "MH", "UP"
    
    # Spatial field - stores polygon/multipolygon geometry
    geometry = gis_models.MultiPolygonField(srid=4326)
    
    # Demographics
    population = models.BigIntegerField(null=True, blank=True)
    male_population = models.BigIntegerField(null=True, blank=True)
    female_population = models.BigIntegerField(null=True, blank=True)
    sex_ratio = models.IntegerField(null=True, blank=True)
    rural_population = models.BigIntegerField(null=True, blank=True)
    urban_population = models.BigIntegerField(null=True, blank=True)
    area_km2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    population_density = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Centroid for marker placement
    centroid = gis_models.PointField(srid=4326, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Auto-calculate centroid if not set
        if not self.centroid and self.geometry:
            self.centroid = self.geometry.centroid
        super().save(*args, **kwargs)


class District(gis_models.Model):
    """Indian Districts with geometric boundaries"""
    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='districts')
    
    # Spatial field
    geometry = gis_models.MultiPolygonField(srid=4326)
    centroid = gis_models.PointField(srid=4326, null=True, blank=True)
    
    # Demographics
    population = models.BigIntegerField(null=True, blank=True)
    growth_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    sex_ratio = models.IntegerField(null=True, blank=True)
    literacy_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    area_km2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['state__name', 'name']
        unique_together = [['name', 'state']]
        indexes = [
            models.Index(fields=['state', 'name']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.state.name}"
    
    def save(self, *args, **kwargs):
        if not self.centroid and self.geometry:
            self.centroid = self.geometry.centroid
        super().save(*args, **kwargs)


class EconomicIndicator(gis_models.Model):
    """Economic data for states/districts"""
    AREA_CHOICES = [
        ('RURAL', 'Rural'),
        ('URBAN', 'Urban'),
        ('COMBINED', 'Combined'),
    ]
    
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='economic_indicators')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True, 
                                 related_name='economic_indicators')
    
    # Time dimension
    year = models.IntegerField(null=True, blank=True)
    month = models.IntegerField(null=True, blank=True)
    date_recorded = models.DateField(null=True, blank=True)
    
    # Economic metrics
    area_type = models.CharField(max_length=20, choices=AREA_CHOICES, default='COMBINED')
    unemployment_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    employment_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estimated_employed = models.BigIntegerField(null=True, blank=True)
    labour_participation_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_monthly_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['-date_recorded', 'state__name']
        indexes = [
            models.Index(fields=['state', 'area_type', 'date_recorded']),
            models.Index(fields=['district', 'area_type', 'date_recorded']),
        ]
    
    def __str__(self):
        location = f"{self.district.name}, " if self.district else ""
        return f"{location}{self.state.name} - {self.area_type} ({self.date_recorded})"


class DemographicProfile(gis_models.Model):
    """Demographic and spending profiles by location"""
    AGE_GROUP_CHOICES = [
        ('18-24', '18-24'),
        ('25-34', '25-34'),
        ('35-44', '35-44'),
        ('45-54', '45-54'),
        ('55+', '55+'),
    ]
    
    EDUCATION_CHOICES = [
        ('HIGH_SCHOOL', 'High School'),
        ('BACHELOR', 'Bachelor'),
        ('MASTER', 'Master'),
        ('PHD', 'PhD'),
    ]
    
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='demographic_profiles')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='demographic_profiles')
    
    # Demographics
    age_group = models.CharField(max_length=20, choices=AGE_GROUP_CHOICES, null=True, blank=True)
    education_level = models.CharField(max_length=50, choices=EDUCATION_CHOICES, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    
    # Income & Spending
    avg_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    avg_disposable_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Expenditure Categories (from Indian_Personal_Finance.csv)
    groceries_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    transport_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    eating_out_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    entertainment_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    utilities_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    healthcare_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    education_expenditure = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Consumer Behavior
    avg_purchase_frequency = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_spending = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    sample_size = models.IntegerField(default=0, help_text="Number of data points aggregated")
    
    class Meta:
        ordering = ['state__name', 'age_group']
        indexes = [
            models.Index(fields=['state', 'age_group', 'education_level']),
            models.Index(fields=['district', 'age_group']),
        ]
    
    def __str__(self):
        location = f"{self.district.name}, " if self.district else ""
        return f"{location}{self.state.name} - {self.age_group or 'All Ages'}"


class IndustryEmployment(gis_models.Model):
    """Employment data by industry and location"""
    INDUSTRY_CHOICES = [
        ('RETAIL', 'Retail'),
        ('HOSPITALITY', 'Hospitality'),
        ('TECHNOLOGY', 'Technology'),
        ('HEALTHCARE', 'Healthcare'),
        ('EDUCATION', 'Education'),
        ('MANUFACTURING', 'Manufacturing'),
        ('FINANCE', 'Finance'),
        ('AGRICULTURE', 'Agriculture'),
        ('CONSTRUCTION', 'Construction'),
        ('OTHER', 'Other'),
    ]
    
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='industry_employment')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='industry_employment')
    
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    employed_count = models.IntegerField(null=True, blank=True)
    unemployed_count = models.IntegerField(null=True, blank=True)
    avg_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    date_recorded = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['state__name', 'industry']
        indexes = [
            models.Index(fields=['state', 'industry']),
            models.Index(fields=['industry', 'date_recorded']),
        ]
    
    def __str__(self):
        return f"{self.industry} in {self.state.name}"


class MarketPotentialZone(gis_models.Model):
    """Calculated market potential zones based on product type and demographics"""
    POTENTIAL_LEVEL_CHOICES = [
        ('HIGH', 'High Potential'),
        ('MEDIUM', 'Medium Potential'),
        ('LOW', 'Low Potential'),
    ]
    
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='market_zones')
    district = models.ForeignKey(District, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name='market_zones')
    
    # Product targeting
    product_type = models.CharField(max_length=100)
    product_category = models.CharField(max_length=100, null=True, blank=True)
    target_age_group = models.CharField(max_length=20, null=True, blank=True)
    target_income_range = models.CharField(max_length=50, null=True, blank=True)
    
    # Calculated metrics
    potential_level = models.CharField(max_length=20, choices=POTENTIAL_LEVEL_CHOICES)
    market_score = models.DecimalField(max_digits=5, decimal_places=2, 
                                       help_text="0-100 score indicating market potential")
    predicted_reach_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    estimated_target_population = models.BigIntegerField(null=True, blank=True)
    
    # Spatial analysis results
    zone_geometry = gis_models.MultiPolygonField(srid=4326, null=True, blank=True,
                                            help_text="Specific high-potential zones within district")
    
    # ML integration
    prediction_request = models.ForeignKey('core.PredictionRequest', on_delete=models.SET_NULL, 
                                          null=True, blank=True, related_name='market_zones')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-market_score', 'state__name']
        indexes = [
            models.Index(fields=['product_type', 'potential_level']),
            models.Index(fields=['state', 'market_score']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        location = f"{self.district.name}, " if self.district else ""
        return f"{self.product_type} in {location}{self.state.name} - {self.potential_level}"


class SpatialQuery(gis_models.Model):
    """Log spatial queries for analytics and caching"""
    from core.models import User
    
    user = models.ForeignKey('core.User', on_delete=models.CASCADE, null=True, blank=True)
    
    # Query parameters
    query_type = models.CharField(max_length=50, 
                                  help_text="e.g., 'nearby_districts', 'within_radius', 'contains_point'")
    reference_point = gis_models.PointField(srid=4326, null=True, blank=True)
    search_radius_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    search_polygon = gis_models.PolygonField(srid=4326, null=True, blank=True)
    
    # Results (cached as JSON)
    result_count = models.IntegerField(default=0)
    result_data = models.JSONField(null=True, blank=True)
    
    # Performance tracking
    execution_time_ms = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.query_type} at {self.created_at}"
