from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import State, District, MarketPotentialZone
from . import utils
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def get_map_context(user=None, form_data=None):
    """
    Get map data and configuration for templates
    
    Args:
        user: Django user object
        form_data: Dictionary with keys: product_type, luxury_level, target_audience, price
    
    Returns:
        Dictionary with map configuration and data
    """
    
    # If form data provided, calculate and store predictions
    if user and form_data and all(k in form_data for k in ['product_type', 'luxury_level', 'target_audience', 'price']):
        try:
            utils.calculate_and_store_match_scores(
                user=user,
                product_type=form_data['product_type'],
                luxury_level=form_data['luxury_level'],
                target_audience=form_data['target_audience'],
                price=form_data['price']
            )
        except Exception as e:
            print(f"Error calculating match scores: {e}")
    
    # Get precomputed metrics from database
    state_metrics = utils.get_region_metrics_for_map('state')
    district_metrics = utils.get_region_metrics_for_map('district')
    
    # Extract match scores for backward compatibility
    match_scores = {}
    for name, metrics in state_metrics.items():
        if metrics['avg_predicted_success'] is not None:
            match_scores[name] = metrics['avg_predicted_success'] * 100
    
    # Get clusters with match scores
    clusters = utils.get_enhanced_clusters_data(match_scores)
    
    # Get map configuration
    map_config = utils.get_complete_map_config()
    
    return {
        'map_config': json.dumps(map_config, cls=DecimalEncoder),
        'clusters': json.dumps(clusters, cls=DecimalEncoder),
        'state_demographics': json.dumps(state_metrics, cls=DecimalEncoder),
        'district_demographics': json.dumps(district_metrics, cls=DecimalEncoder),
        'match_scores': json.dumps(match_scores, cls=DecimalEncoder)
    }


def map_view(request, context=None):
    """Main interactive map view with dynamic data from PostGIS"""
    if context is None:
        context = {}
    
    # Get initial data for map
    states_count = State.objects.count()
    districts_count = District.objects.count()
    
    # Get map context data
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
    
    geojson_data = utils.export_states_geojson(include_demographics=include_demographics)
    
    return JsonResponse(geojson_data, safe=False)


@require_http_methods(["GET"])
def api_districts_geojson(request):
    """API endpoint to get districts as GeoJSON"""
    state_name = request.GET.get('state', None)
    include_metrics = request.GET.get('metrics', 'true').lower() == 'true'
    
    geojson_data = utils.export_districts_geojson(
        state_name=state_name,
        include_metrics=include_metrics
    )
    
    return JsonResponse(geojson_data, safe=False)


@require_http_methods(["GET"])
def api_market_zones(request):
    """API endpoint to get market potential zones"""
    product_type = request.GET.get('product_type', None)
    
    geojson_data = utils.export_market_zones_geojson(product_type=product_type)
    
    return JsonResponse(geojson_data, safe=False)


# ==================== Spatial Query Endpoints ====================

@require_http_methods(["GET"])
def api_districts_nearby(request):
    """Find districts within radius of a point"""
    try:
        lat = float(request.GET.get('lat'))
        lng = float(request.GET.get('lng'))
        radius_km = int(float(request.GET.get('radius', 50)))
        
        districts = utils.get_districts_within_radius(lat, lng, radius_km)
        
        data = {
            'count': districts.count(),
            'districts': [
                {
                    'id': d.id,
                    'name': d.name,
                    'state': d.state.name,
                    'distance_km': round(float(d.distance_km), 2) if hasattr(d, 'distance_km') else 0,
                    'population': d.population,
                    'coordinates': {
                        'lat': d.centroid.y if d.centroid else 0,
                        'lng': d.centroid.x if d.centroid else 0
                    }
                }
                for d in districts
            ]
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
        
        state = utils.get_state_containing_point(lat, lng)
        district = utils.get_district_containing_point(lat, lng)
        
        data = {
            'state': {
                'id': state.id,
                'name': state.name,
                'population': state.population
            } if state else None,
            'district': {
                'id': district.id,
                'name': district.name,
                'population': district.population,
                'literacy_rate': float(district.literacy_rate) if district.literacy_rate else 0
            } if district else None
        }
        
        return JsonResponse(data)
    
    except (ValueError, TypeError) as e:
        return JsonResponse({'error': f'Invalid parameters: {str(e)}'}, status=400)


@require_http_methods(["GET"])
def api_neighboring_districts(request):
    """Get neighboring districts"""
    try:
        district_id = int(request.GET.get('district_id'))
        
        neighbors = utils.get_neighboring_districts(district_id)
        
        data = {
            'count': neighbors.count(),
            'neighbors': [
                {
                    'id': n.id,
                    'name': n.name,
                    'state': n.state.name,
                    'population': n.population
                }
                for n in neighbors
            ]
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
        
        result = utils.analyze_market_corridor(
            start_lat=data['start_lat'],
            start_lng=data['start_lng'],
            end_lat=data['end_lat'],
            end_lng=data['end_lng'],
            buffer_km=data.get('buffer_km', 20)
        )
        
        return JsonResponse(result)
    
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
        
        analysis = utils.calculate_market_reach_radius(
            district_id=district_id,
            product_type=product_type,
            target_demographics=target_demographics
        )
        
        return JsonResponse({'analysis': analysis}, safe=False)
    
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