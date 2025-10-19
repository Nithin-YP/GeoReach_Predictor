from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'geo'

def geo_home(request):
    """Redirect /geo/ to /geo/map/"""
    return redirect('geo:map')

urlpatterns = [
    # Root geo endpoint - redirects to map
    path('', geo_home, name='geo_home'),
    
    # Main map view
    path('map/', views.map_view, name='map'),
    
    # GeoJSON API endpoints
    path('api/states/geojson/', views.api_states_geojson, name='api_states_geojson'),
    path('api/districts/geojson/', views.api_districts_geojson, name='api_districts_geojson'),
    path('api/market-zones/', views.api_market_zones, name='api_market_zones'),
    
    # Spatial query endpoints
    path('api/districts/nearby/', views.api_districts_nearby, name='api_districts_nearby'),
    path('api/point-location/', views.api_point_location, name='api_point_location'),
    path('api/neighboring-districts/', views.api_neighboring_districts, name='api_neighboring_districts'),
    
    # Business intelligence endpoints
    path('api/demographic-heatmap/', views.api_demographic_heatmap, name='api_demographic_heatmap'),
    path('api/employment-hotspots/', views.api_employment_hotspots, name='api_employment_hotspots'),
    path('api/analyze-corridor/', views.api_analyze_corridor, name='api_analyze_corridor'),
    path('api/market-reach-analysis/', views.api_market_reach_analysis, name='api_market_reach_analysis'),
    path('api/high-potential-zones/', views.api_high_potential_zones, name='api_high_potential_zones'),
] 