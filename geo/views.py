from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import State, District, MarketPotentialZone
from . import utils
from . import sql as sqlapi
import json


def get_map_context(request_params=None):
    """Generate context data for map visualization"""
    clusters = utils.get_enhanced_clusters_data()
    config = utils.get_complete_map_config()
    
    return {
        'clusters': json.dumps(clusters),
        'map_config': json.dumps(config),
    }


def map_view(request, context=None):
    """Main interactive map view with dynamic data from PostGIS"""
    if context is None:
        context = {}
    
    # Get initial data for map
    states_count = State.objects.count()
    districts_count = District.objects.count()
    
    map_context = get_map_context()
    context.update(map_context)
    context.update({
        'states_count': states_count,
        'districts_count': districts_count,
    })
    
    return render(request, "geo/map.html", context)


# ==================== GeoJSON API Endpoints ====================

@require_http_methods(["GET"])
def api_states_geojson(request):
    """API endpoint to get states as GeoJSON"""
    include_demographics = request.GET.get('demographics', 'true').lower() == 'true'
    # Prefer SQL-based GeoJSON for performance; fallback to utils if demographics requested
    if include_demographics:
        geojson_data = utils.export_states_geojson(include_demographics=include_demographics)
    else:
        geojson_data = sqlapi.states_geojson()
    
    return JsonResponse(geojson_data, safe=False)


@require_http_methods(["GET"])
def api_districts_geojson(request):
    """API endpoint to get districts as GeoJSON"""
    state_name = request.GET.get('state', None)
    include_metrics = request.GET.get('metrics', 'true').lower() == 'true'
    # Use SQL path when metrics aren't needed
    if include_metrics:
        geojson_data = utils.export_districts_geojson(
            state_name=state_name,
            include_metrics=include_metrics
        )
    else:
        geojson_data = sqlapi.districts_geojson(state_name=state_name)
    
    return JsonResponse(geojson_data, safe=False)


@require_http_methods(["GET"])
def api_market_zones(request):
    """API endpoint to get market potential zones"""
    product_type = request.GET.get('product_type', None)
    geojson_data = sqlapi.market_zones_geojson(product_type=product_type)
    
    return JsonResponse(geojson_data, safe=False)


# ==================== Spatial Query Endpoints ====================

@require_http_methods(["GET"])
def api_districts_nearby(request):
    """Find districts within radius of a point"""
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        radius_km = float(request.GET.get('radius', 50))
        rows = sqlapi.districts_within_radius(lat, lng, radius_km)
        data = {
            'count': len(rows),
            'districts': rows
        }
        
        return JsonResponse(data)
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid parameters: {str(e)}'}, status=400)


@require_http_methods(["GET"])
def api_point_location(request):
    """Get state and district for a given point"""
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        state = sqlapi.state_containing_point(lat, lng)
        district = sqlapi.district_containing_point(lat, lng)
        data = {
            'state': state,
            'district': district,
        }
        
        return JsonResponse(data)
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid parameters: {str(e)}'}, status=400)


@require_http_methods(["GET"])
def api_neighboring_districts(request):
    """Get neighboring districts"""
    try:
        district_id = int(request.GET.get('district_id'))
        neighbors = sqlapi.neighboring_districts(district_id)
        data = {
            'count': len(neighbors),
            'neighbors': neighbors
        }
        
        return JsonResponse(data)
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid district_id: {str(e)}'}, status=400)


# ==================== Business Intelligence Endpoints ====================

@require_http_methods(["GET"])
def api_demographic_heatmap(request):
    """Get demographic heatmap data"""
    age_group = request.GET.get('age_group', None)
    city_tier = request.GET.get('city_tier', None)
    
    heatmap_data = utils.get_demographic_heatmap_data(
        age_group=age_group,
        city_tier=city_tier
    )
    
    return JsonResponse(heatmap_data, safe=False)


@require_http_methods(["GET"])
def api_employment_hotspots(request):
    """Get employment hotspots for an industry"""
    industry = request.GET.get('industry', 'RETAIL')
    min_employed = int(request.GET.get('min_employed', 100))
    
    hotspots = utils.get_employment_hotspots_by_industry(industry, min_employed)
    
    return JsonResponse({'hotspots': hotspots}, safe=False)


@require_http_methods(["POST"])
@csrf_exempt  # For testing - remove in production and use proper CSRF handling
def api_analyze_corridor(request):
    """Analyze market potential along a corridor"""
    try:
        data = json.loads(request.body)
        
        rows = sqlapi.analyze_market_corridor(
            start_lat=data['start_lat'],
            start_lng=data['start_lng'],
            end_lat=data['end_lat'],
            end_lng=data['end_lng'],
            buffer_km=data.get('buffer_km', 20)
        )
        return JsonResponse({'count': len(rows), 'districts': rows})
    
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return JsonResponse({'error': f'Invalid request data: {str(e)}'}, status=400)


@require_http_methods(["GET"])
@login_required
def api_market_reach_analysis(request):
    """Analyze optimal market reach from a district"""
    try:
        district_id = int(request.GET.get('district_id'))
        product_type = request.GET.get('product_type')
        
        # Parse target demographics
        target_demographics = {}
        if request.GET.get('age_group'):
            target_demographics['age_group'] = request.GET.get('age_group')
        if request.GET.get('city_tier'):
            target_demographics['city_tier'] = request.GET.get('city_tier')
        
        # SQL version returns districts within the radius; choose a default radius
        radius_km = float(request.GET.get('radius_km', 100))
        rows = sqlapi.market_reach_radius(district_id, radius_km)
        return JsonResponse({'radius_km': radius_km, 'districts': rows}, safe=False)
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid parameters: {str(e)}'}, status=400)


@require_http_methods(["GET"])
def api_high_potential_zones(request):
    """Get high potential zones for a product"""
    product_type = request.GET.get('product_type')
    min_score = float(request.GET.get('min_score', 60))
    
    if not product_type:
        return JsonResponse({'error': 'product_type is required'}, status=400)
    
    zones = utils.get_high_potential_zones_for_product(product_type, min_score)
    
    data = {
        'count': zones.count(),
        'zones': [
            {
                'id': z.id,
                'state': z.state.name,
                'district': z.district.name if z.district else None,
                'potential_level': z.potential_level,
                'market_score': float(z.market_score),
                'predicted_reach': float(z.predicted_reach_percentage) if z.predicted_reach_percentage else 0,
                'coordinates': {
                    'lat': z.district.centroid.y if z.district and z.district.centroid else 0,
                    'lng': z.district.centroid.x if z.district and z.district.centroid else 0
                }
            }
            for z in zones
        ]
    }
    
    return JsonResponse(data)


# ==================== SQL-backed Dashboard analytics endpoints ====================

@require_http_methods(["GET"])
def api_sql_population_density_geojson(request):
    state = request.GET.get('state')
    return JsonResponse(sqlapi.b1_population_density_geojson(state_name=state), safe=False)


@require_http_methods(["GET"])
def api_sql_spending_choropleth_geojson(request):
    state = request.GET.get('state')
    return JsonResponse(sqlapi.b2_spending_choropleth_geojson(state_name=state), safe=False)


@require_http_methods(["GET"])
def api_sql_unemployment_bubbles_geojson(request):
    state = request.GET.get('state')
    return JsonResponse(sqlapi.b3_unemployment_bubbles_geojson(state_name=state), safe=False)


@require_http_methods(["GET"])
def api_sql_top_spending_cities(request):
    limit = int(request.GET.get('limit', 10))
    return JsonResponse(sqlapi.b4_top_spending_cities(limit=limit), safe=False)


@require_http_methods(["GET"])
def api_sql_savings_leaderboard(request):
    limit = int(request.GET.get('limit', 10))
    return JsonResponse(sqlapi.b5_savings_leaderboard(limit=limit), safe=False)


@require_http_methods(["GET"])
def api_sql_whitespaces_geojson(request):
    product_type = request.GET.get('product_type')
    return JsonResponse(sqlapi.b6_whitespaces_geojson(product_type=product_type), safe=False)


@require_http_methods(["GET"])
def api_sql_literacy_income_scatter(request):
    return JsonResponse(sqlapi.b7_literacy_income_scatter(), safe=False)


@require_http_methods(["GET"])
def api_sql_market_accessibility_geojson(request):
    w_pd = float(request.GET.get('w_popdens', 1.0))
    w_inc = float(request.GET.get('w_income', 1.0))
    w_er = float(request.GET.get('w_emprate', 1.0))
    return JsonResponse(sqlapi.b8_market_accessibility_geojson(w_pd, w_inc, w_er), safe=False)


@require_http_methods(["GET"])
def api_sql_avg_disposable_income_geojson(request):
    return JsonResponse(sqlapi.b9_avg_disposable_income_geojson(), safe=False)


@require_http_methods(["GET"])
def api_sql_affordability_index_geojson(request):
    return JsonResponse(sqlapi.b10_affordability_index_geojson(), safe=False)


@require_http_methods(["GET"])
def api_sql_spending_elasticity(request):
    return JsonResponse(sqlapi.b11_spending_elasticity(), safe=False)


@require_http_methods(["GET"])
def api_sql_purchase_frequency_geojson(request):
    return JsonResponse(sqlapi.b12_purchase_frequency_geojson(), safe=False)


@require_http_methods(["GET"])
def api_sql_profitability_proxy_by_state(request):
    return JsonResponse(sqlapi.b13_profitability_proxy_by_state(), safe=False)


@require_http_methods(["GET"])
def api_sql_hri_geojson(request):
    w_spend = float(request.GET.get('w_spend', 1.0))
    w_emp = float(request.GET.get('w_emp', 1.0))
    return JsonResponse(sqlapi.b14_hri_geojson(w_spend, w_emp), safe=False)


@require_http_methods(["GET"])
def api_sql_district_penetration_rate(request):
    return JsonResponse(sqlapi.b15_district_penetration_rate(), safe=False)


@require_http_methods(["GET"])
def api_sql_geo_concentration_index(request):
    return JsonResponse(sqlapi.b16_geo_concentration_index(), safe=False)


@require_http_methods(["GET"])
def api_sql_expansion_opportunity_geojson(request):
    product_type = request.GET.get('product_type')
    w_pd = float(request.GET.get('w_pd', 1.0))
    w_income = float(request.GET.get('w_income', 1.0))
    w_lowpen = float(request.GET.get('w_lowpen', 1.0))
    return JsonResponse(sqlapi.b17_expansion_opportunity_geojson(product_type, w_pd, w_income, w_lowpen), safe=False)


# ==================== Dashboard Page (SQL-driven) ====================

def dashboard_view(request):
    """Dashboard UI rendering SQL-backed layers and analytics."""
    return render(request, "geo/dashboard.html")


# ==================== Additional SQL endpoints for tools ====================

@require_http_methods(["POST"])
@csrf_exempt
def api_sql_states_intersecting_area(request):
    try:
        payload = json.loads(request.body)
        polygon_geojson = payload.get('polygon') or payload
        rows = sqlapi.states_intersecting_area(polygon_geojson)
        return JsonResponse({'count': len(rows), 'states': rows})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


@require_http_methods(["GET"])
def api_sql_distance_between_districts(request):
    try:
        d1 = int(request.GET.get('district_id_1'))
        d2 = int(request.GET.get('district_id_2'))
        result = sqlapi.distance_between_districts(d1, d2)
        if result is None:
            return JsonResponse({'error': 'Invalid district ids'}, status=404)
        return JsonResponse(result)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'district_id_1 and district_id_2 are required integers'}, status=400)


@require_http_methods(["GET"])
def api_sql_competitive_density_map(request):
    try:
        product_type = request.GET.get('product_type')
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        radius_km = float(request.GET.get('radius_km', 100))
        rows = sqlapi.competitive_density_map(product_type, lat, lng, radius_km)
        return JsonResponse({'count': len(rows), 'zones': rows})
    except (TypeError, ValueError):
        return JsonResponse({'error': 'product_type, lat, lng required'}, status=400)