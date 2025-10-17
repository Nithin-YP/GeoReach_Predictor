from django.contrib.gis import admin
from .models import (State, District, EconomicIndicator, DemographicProfile, 
                     IndustryEmployment, MarketPotentialZone, SpatialQuery)


@admin.register(State)
class StateAdmin(admin.GISModelAdmin):
    list_display = ['name', 'code', 'population', 'population_density', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['centroid', 'created_at', 'updated_at']
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 5,
            'default_lat': 20.5937,
            'default_lon': 78.9629,
        },
    }


@admin.register(District)
class DistrictAdmin(admin.GISModelAdmin):
    list_display = ['name', 'state', 'population', 'literacy_rate', 'created_at']
    list_filter = ['state', 'created_at']
    search_fields = ['name', 'state__name']
    readonly_fields = ['centroid', 'created_at', 'updated_at']
    autocomplete_fields = ['state']
    gis_widget_kwargs = {
        'attrs': {
            'default_zoom': 7,
            'default_lat': 20.5937,
            'default_lon': 78.9629,
        },
    }


@admin.register(EconomicIndicator)
class EconomicIndicatorAdmin(admin.ModelAdmin):
    list_display = ['state', 'district', 'area_type', 'unemployment_rate', 'employment_rate', 'date_recorded']
    list_filter = ['area_type', 'state', 'date_recorded']
    search_fields = ['state__name', 'district__name']
    autocomplete_fields = ['state', 'district']
    date_hierarchy = 'date_recorded'


@admin.register(DemographicProfile)
class DemographicProfileAdmin(admin.ModelAdmin):
    list_display = ['state', 'district', 'age_group', 'city_tier', 'avg_income', 'sample_size']
    list_filter = ['age_group', 'city_tier', 'education_level', 'state']
    search_fields = ['state__name', 'district__name', 'occupation']
    autocomplete_fields = ['state', 'district']


@admin.register(IndustryEmployment)
class IndustryEmploymentAdmin(admin.ModelAdmin):
    list_display = ['industry', 'state', 'district', 'employed_count', 'unemployed_count', 'avg_salary']
    list_filter = ['industry', 'state', 'date_recorded']
    search_fields = ['state__name', 'district__name']
    autocomplete_fields = ['state', 'district']
    date_hierarchy = 'date_recorded'


@admin.register(MarketPotentialZone)
class MarketPotentialZoneAdmin(admin.GISModelAdmin):
    list_display = ['product_type', 'state', 'district', 'potential_level', 'market_score', 'created_at']
    list_filter = ['potential_level', 'product_type', 'state', 'created_at']
    search_fields = ['product_type', 'product_category', 'state__name', 'district__name']
    autocomplete_fields = ['state', 'district', 'prediction_request']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(SpatialQuery)
class SpatialQueryAdmin(admin.GISModelAdmin):
    list_display = ['query_type', 'user', 'result_count', 'execution_time_ms', 'created_at']
    list_filter = ['query_type', 'created_at']
    search_fields = ['query_type', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
