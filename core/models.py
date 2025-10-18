from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text=
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.',
        related_name="core_user_set", # Custom related_name
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="core_user_permissions_set", # Custom related_name
        related_query_name="user",
    )
    is_blocked = models.BooleanField(default=False, help_text='Designates whether this user should be treated as blocked.')


class PredictionRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_type = models.CharField(max_length=100)
    product_luxury = models.CharField(max_length=50)
    target_audience = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    region = models.CharField(max_length=100)
    request_timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Prediction Request for {self.product_type} by {self.user.username} in {self.region}"

class PredictionResult(models.Model):
    prediction_request = models.OneToOneField(PredictionRequest, on_delete=models.CASCADE)
    predicted_reach = models.DecimalField(max_digits=5, decimal_places=2) # Percentage
    success_probability = models.DecimalField(max_digits=4, decimal_places=3) # 0-1 score
    model_confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Result for Request {self.prediction_request.id}: Reach {self.predicted_reach}%, Probability {self.success_probability}"

class Cluster(models.Model):
    prediction_result = models.ForeignKey(PredictionResult, on_delete=models.CASCADE)
    # Temporarily using DecimalField for latitude and longitude
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    cluster_label = models.CharField(max_length=50) # e.g., High, Medium, Low
    population_density = models.IntegerField(null=True, blank=True)
    avg_income = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    employment_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True) # Percentage
    interest_index = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)

    def __str__(self):
        return f"Cluster {self.cluster_label} for Result {self.prediction_result.id} at ({self.latitude}, {self.longitude})"

class Dataset(models.Model):
    name = models.CharField(max_length=255)
    source = models.CharField(max_length=255, null=True, blank=True)
    upload_date = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(auto_now=True)
    feature_list = models.JSONField(null=True, blank=True) # Store list of features as JSON
    record_count = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.name

class ModelVersion(models.Model):
    """Track ML model versions and metadata"""
    model_version = models.CharField(max_length=50, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True, null=True)
    training_data_summary = models.JSONField(blank=True, null=True)
    validation_metrics = models.JSONField(blank=True, null=True)
    
    class Meta:
        db_table = 'model_versions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Model {self.model_version}"


class RegionMetrics(models.Model):
    """Precomputed metrics for states and districts"""
    REGION_TYPES = [
        ('state', 'State'),
        ('district', 'District'),
    ]
    
    region_type = models.CharField(max_length=10, choices=REGION_TYPES)
    region_id = models.IntegerField()  # state_id or district_id
    region_name = models.CharField(max_length=255)  # For easy lookup
    
    # Model predictions
    model_version = models.CharField(max_length=50, blank=True, null=True)
    avg_predicted_success = models.DecimalField(max_digits=5, decimal_places=4, blank=True, null=True)  # 0-1
    avg_predicted_reach = models.DecimalField(max_digits=5, decimal_places=4, blank=True, null=True)  # 0-1
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, blank=True, null=True)  # 0-1
    data_coverage = models.DecimalField(max_digits=5, decimal_places=4, blank=True, null=True)  # 0-1
    
    # Economic metrics
    spending_index = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    avg_income = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    avg_spending = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    
    # Demographics
    population_density = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    literacy_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    employment_rate = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Competition
    competitor_count = models.IntegerField(default=0)
    
    # Explainability
    top_drivers = models.JSONField(blank=True, null=True)  # [{"feature":"income","weight":0.42}, ...]
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'region_metrics'
        unique_together = [['region_type', 'region_id']]
        indexes = [
            models.Index(fields=['region_type', 'region_id']),
            models.Index(fields=['region_name']),
        ]
    
    def __str__(self):
        return f"{self.region_type.title()}: {self.region_name}"


class ProductPrediction(models.Model):
    """Individual predictions for specific products and regions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Product details
    product_type = models.CharField(max_length=100)
    luxury_level = models.CharField(max_length=50)
    target_audience = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Region
    region_type = models.CharField(max_length=10, choices=[('state', 'State'), ('district', 'District')])
    region_id = models.IntegerField()
    region_name = models.CharField(max_length=255)
    
    # Predictions
    predicted_success = models.DecimalField(max_digits=5, decimal_places=4)  # 0-1
    predicted_reach = models.DecimalField(max_digits=5, decimal_places=4)  # 0-1
    confidence = models.DecimalField(max_digits=5, decimal_places=4, default=0.5)
    
    # Model info
    model_version = models.CharField(max_length=50, default='v1.0')
    
    # Explainability
    feature_importance = models.JSONField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_predictions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'region_type', 'region_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.product_type} in {self.region_name} - {self.predicted_success}"