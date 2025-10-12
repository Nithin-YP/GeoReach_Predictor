from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PredictionRequest, PredictionResult, Cluster, Dataset

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active', 'is_superuser', 'is_blocked')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('is_blocked',)}),
    )

@admin.register(PredictionRequest)
class PredictionRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'product_type', 'region', 'request_timestamp')
    list_filter = ('product_type', 'region', 'request_timestamp')
    search_fields = ('user__username', 'product_type', 'region')

@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ('prediction_request', 'predicted_reach', 'success_probability', 'created_at')
    list_filter = ('predicted_reach', 'success_probability', 'created_at')
    search_fields = ('prediction_request__user__username', 'prediction_request__product_type')

@admin.register(Cluster)
class ClusterAdmin(admin.ModelAdmin):
    list_display = ('prediction_result', 'cluster_label', 'latitude', 'longitude', 'population_density', 'avg_income')
    list_filter = ('cluster_label', 'population_density')
    search_fields = ('prediction_result__prediction_request__user__username', 'cluster_label')

@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ('name', 'source', 'upload_date', 'last_updated', 'record_count')
    list_filter = ('source', 'upload_date')
    search_fields = ('name', 'source')