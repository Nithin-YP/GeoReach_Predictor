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
    path('api/<str:region_type>/<int:region_id>/details/', views.region_details_api, name='region_details_api'),
    path('api/<str:region_type>/<int:region_id>/demographics/', views.region_demographics_api, name='region_demographics_api'),
    path('api/<str:region_type>/<int:region_id>/economic/', views.region_economic_api, name='region_economic_api'),
    path('api/<str:region_type>/<int:region_id>/export/', views.region_export_api, name='region_export_api'),

    # SQL-backed analytics endpoints
    path('api/sql/population-density/', views.api_sql_population_density_geojson, name='api_sql_population_density_geojson'),
    path('api/sql/spending-choropleth/', views.api_sql_spending_choropleth_geojson, name='api_sql_spending_choropleth_geojson'),
    path('api/sql/unemployment-bubbles/', views.api_sql_unemployment_bubbles_geojson, name='api_sql_unemployment_bubbles_geojson'),
    path('api/sql/top-spending-cities/', views.api_sql_top_spending_cities, name='api_sql_top_spending_cities'),
    path('api/sql/savings-leaderboard/', views.api_sql_savings_leaderboard, name='api_sql_savings_leaderboard'),
    path('api/sql/whitespaces/', views.api_sql_whitespaces_geojson, name='api_sql_whitespaces_geojson'),
    path('api/sql/literacy-income/', views.api_sql_literacy_income_scatter, name='api_sql_literacy_income_scatter'),
    path('api/sql/market-accessibility/', views.api_sql_market_accessibility_geojson, name='api_sql_market_accessibility_geojson'),
    path('api/sql/avg-disposable-income/', views.api_sql_avg_disposable_income_geojson, name='api_sql_avg_disposable_income_geojson'),
    path('api/sql/affordability-index/', views.api_sql_affordability_index_geojson, name='api_sql_affordability_index_geojson'),
    path('api/sql/spending-elasticity/', views.api_sql_spending_elasticity, name='api_sql_spending_elasticity'),
    path('api/sql/purchase-frequency/', views.api_sql_purchase_frequency_geojson, name='api_sql_purchase_frequency_geojson'),
    path('api/sql/profitability-proxy/', views.api_sql_profitability_proxy_by_state, name='api_sql_profitability_proxy_by_state'),
    path('api/sql/hri/', views.api_sql_hri_geojson, name='api_sql_hri_geojson'),
    path('api/sql/district-penetration/', views.api_sql_district_penetration_rate, name='api_sql_district_penetration_rate'),
    path('api/sql/geo-concentration-index/', views.api_sql_geo_concentration_index, name='api_sql_geo_concentration_index'),
    path('api/sql/expansion-opportunity/', views.api_sql_expansion_opportunity_geojson, name='api_sql_expansion_opportunity_geojson'),
    path('api/sql/states-intersecting-area/', views.api_sql_states_intersecting_area, name='api_sql_states_intersecting_area'),
    path('api/sql/distance-between-districts/', views.api_sql_distance_between_districts, name='api_sql_distance_between_districts'),
    path('api/sql/competitive-density/', views.api_sql_competitive_density_map, name='api_sql_competitive_density_map'),

    # Dashboard page (SQL-driven)
    path('dashboard/', views.dashboard_view, name='dashboard'),
] 