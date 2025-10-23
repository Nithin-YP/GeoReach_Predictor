from django.contrib.gis.geos import Point, GEOSGeometry, LineString
from django.contrib.gis.measure import D  # Distance
from django.contrib.gis.db.models.functions import Distance, Area
from django.db.models import Avg, Sum, Count, Q, F
from .models import (State, District, EconomicIndicator, DemographicProfile, 
                     IndustryEmployment, MarketPotentialZone)
import json


# ==================== BASIC SPATIAL QUERIES ====================

def get_districts_within_radius(latitude, longitude, radius_km=50):
    """
    Find all districts within a given radius from a point.
    
    PostGIS Query: ST_Distance with geographic calculations
    Uses ST_Distance which automatically handles geographic coordinates
    """
    point = Point(longitude, latitude, srid=4326)
    
    # Use Distance function to calculate and filter
    # For geographic coordinates (SRID 4326), distance is calculated in meters
    districts = District.objects.annotate(
        distance_m=Distance('centroid', point)
    ).filter(
        distance_m__lte=radius_km * 1000  # Convert km to meters
    ).order_by('distance_m')
    
    # Add distance_km for convenience
    districts = districts.annotate(
        distance_km=F('distance_m') / 1000
    )
    
    return districts


def get_state_containing_point(latitude, longitude):
    """
    Find which state contains a given point.
    
    PostGIS Query: ST_Contains
    """
    point = Point(longitude, latitude, srid=4326)
    
    try:
        state = State.objects.get(geometry__contains=point)
        return state
    except State.DoesNotExist:
        return None
    except State.MultipleObjectsReturned:
        # Return the first one if multiple found
        return State.objects.filter(geometry__contains=point).first()


def get_district_containing_point(latitude, longitude):
    """
    Find which district contains a given point.
    
    PostGIS Query: ST_Contains
    """
    point = Point(longitude, latitude, srid=4326)
    
    try:
        district = District.objects.get(geometry__contains=point)
        return district
    except District.DoesNotExist:
        return None
    except District.MultipleObjectsReturned:
        # Return the first one if multiple found
        return District.objects.filter(geometry__contains=point).first()


def get_neighboring_districts(district_id):
    """
    Find all districts that share a boundary with given district.
    
    PostGIS Query: ST_Touches or ST_Intersects
    """
    try:
        district = District.objects.get(id=district_id)
        
        neighbors = District.objects.filter(
            geometry__touches=district.geometry
        ).exclude(id=district_id)
        
        return neighbors
    except District.DoesNotExist:
        return District.objects.none()


def get_states_intersecting_area(polygon_geojson):
    """
    Find all states intersecting with a custom polygon.
    
    PostGIS Query: ST_Intersects
    """
    polygon = GEOSGeometry(json.dumps(polygon_geojson))
    
    states = State.objects.filter(
        geometry__intersects=polygon
    ).annotate(
        intersection_area=Area('geometry')
    ).order_by('-intersection_area')
    
    return states


def calculate_distance_between_districts(district_id_1, district_id_2):
    """
    Calculate distance between centroids of two districts.
    
    PostGIS Query: ST_Distance
    """
    try:
        d1 = District.objects.get(id=district_id_1)
        d2 = District.objects.get(id=district_id_2)
        
        # Distance in meters
        distance_m = d1.centroid.distance(d2.centroid) * 111000  # Approximate conversion
        
        return {
            'district_1': str(d1),
            'district_2': str(d2),
            'distance_km': round(distance_m / 1000, 2)
        }
    except District.DoesNotExist:
        return None


# ==================== BUSINESS INTELLIGENCE QUERIES ====================

def get_high_potential_zones_for_product(product_type, min_score=60):
    """
    Get geographic zones with high market potential for a product.
    
    Combines spatial data with market analysis.
    """
    zones = MarketPotentialZone.objects.filter(
        product_type=product_type,
        market_score__gte=min_score
    ).select_related('state', 'district').order_by('-market_score')
    
    return zones


def get_demographic_heatmap_data(age_group=None, city_tier=None):
    """
    Generate heatmap data for demographic concentrations.
    
    Returns GeoJSON with demographic metrics for visualization.
    """
    filters = {}
    if age_group:
        filters['age_group'] = age_group
    if city_tier:
        filters['city_tier'] = city_tier
    
    profiles = DemographicProfile.objects.filter(**filters).select_related('state', 'district')
    
    features = []
    for profile in profiles:
        if profile.district and profile.district.centroid:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [profile.district.centroid.x, profile.district.centroid.y]
                },
                "properties": {
                    "name": str(profile.district),
                    "avg_income": float(profile.avg_income) if profile.avg_income else 0,
                    "avg_spending": float(profile.avg_spending) if profile.avg_spending else 0,
                    "purchase_frequency": float(profile.avg_purchase_frequency) if profile.avg_purchase_frequency else 0,
                    "sample_size": profile.sample_size
                }
            }
            features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


def analyze_market_corridor(start_lat, start_lng, end_lat, end_lng, buffer_km=20):
    """
    Analyze market potential along a corridor (e.g., highway, railway).
    
    PostGIS Query: ST_Buffer + ST_Intersects
    """
    line = LineString(
        (start_lng, start_lat),
        (end_lng, end_lat),
        srid=4326
    )
    
    # Create buffer around the line
    buffer = line.buffer(buffer_km / 111.0)  # Approximate degree conversion
    
    # Find districts intersecting the corridor
    districts_in_corridor = District.objects.filter(
        geometry__intersects=buffer
    ).select_related('state')
    
    # Aggregate demographics
    total_population = districts_in_corridor.aggregate(
        total_pop=Sum('population')
    )['total_pop']
    
    avg_literacy = districts_in_corridor.aggregate(
        avg_lit=Avg('literacy_rate')
    )['avg_lit']
    
    return {
        'districts_count': districts_in_corridor.count(),
        'districts': list(districts_in_corridor.values('name', 'state__name', 'population')),
        'total_population': total_population,
        'avg_literacy_rate': round(avg_literacy, 2) if avg_literacy else 0
    }


def get_employment_hotspots_by_industry(industry, min_employed=1000):
    """
    Find districts with high employment in specific industry.
    
    Returns geographic data with employment metrics.
    """
    hotspots = IndustryEmployment.objects.filter(
        industry=industry,
        employed_count__gte=min_employed
    ).select_related('state', 'district').order_by('-employed_count')
    
    result = []
    for hotspot in hotspots:
        if hotspot.district and hotspot.district.centroid:
            result.append({
                'district': str(hotspot.district),
                'state': hotspot.state.name,
                'employed_count': hotspot.employed_count,
                'avg_salary': float(hotspot.avg_salary) if hotspot.avg_salary else 0,
                'coordinates': {
                    'lat': hotspot.district.centroid.y,
                    'lng': hotspot.district.centroid.x
                }
            })
    
    return result


def calculate_market_reach_radius(district_id, product_type, target_demographics):
    """
    Calculate optimal marketing radius from a district based on demographics.
    
    Advanced spatial + ML integration query.
    """
    try:
        base_district = District.objects.get(id=district_id)
        base_point = base_district.centroid
        
        # Find similar demographic profiles within expanding radius
        max_radius_km = 200
        radius_step = 25
        
        results = []
        for radius in range(radius_step, max_radius_km + 1, radius_step):
            districts_in_radius = District.objects.filter(
                geometry__dwithin=(base_point, D(km=radius))
            )
            
            # Aggregate target demographics
            demographic_match = DemographicProfile.objects.filter(
                district__in=districts_in_radius,
                **target_demographics
            ).aggregate(
                total_pop=Sum('sample_size'),
                avg_income=Avg('avg_income'),
                avg_spending=Avg('avg_spending')
            )
            
            results.append({
                'radius_km': radius,
                'districts_count': districts_in_radius.count(),
                'target_population': demographic_match['total_pop'] or 0,
                'avg_income': float(demographic_match['avg_income']) if demographic_match['avg_income'] else 0,
                'avg_spending': float(demographic_match['avg_spending']) if demographic_match['avg_spending'] else 0
            })
        
        return results
    
    except District.DoesNotExist:
        return []


def get_competitive_density_map(product_type, lat, lng, radius_km=100):
    """
    Analyze density of market zones for same product type in an area.
    
    Useful for competitive analysis.
    """
    point = Point(lng, lat, srid=4326)
    
    zones = MarketPotentialZone.objects.filter(
        product_type=product_type,
        district__geometry__dwithin=(point, D(km=radius_km))
    ).select_related('district', 'state').annotate(
        distance=Distance('district__centroid', point)
    ).order_by('distance')
    
    return zones


# ==================== DATA EXPORT FOR VISUALIZATION ====================

def export_states_geojson(include_demographics=True):
    """
    Export all states as GeoJSON with demographic data.
    """
    states = State.objects.all()
    
    features = []
    for state in states:
        properties = {
            'id': state.id,
            'name': state.name,
            'code': state.code,
            'population': state.population,
            'density': float(state.population_density) if state.population_density else 0
        }
        
        if include_demographics:
            latest_economic = state.economic_indicators.filter(
                area_type='COMBINED'
            ).order_by('-date_recorded').first()
            
            if latest_economic:
                properties.update({
                    'unemployment_rate': float(latest_economic.unemployment_rate) if latest_economic.unemployment_rate else 0,
                    'avg_salary': float(latest_economic.avg_monthly_salary) if latest_economic.avg_monthly_salary else 0
                })
        
        feature = {
            'type': 'Feature',
            'geometry': json.loads(state.geometry.geojson),
            'properties': properties
        }
        features.append(feature)
    
    return {
        'type': 'FeatureCollection',
        'features': features
    }


def export_districts_geojson(state_name=None, include_metrics=True):
    """
    Export districts as GeoJSON, optionally filtered by state.
    """
    queryset = District.objects.all()
    
    if state_name:
        queryset = queryset.filter(state__name=state_name)
    
    queryset = queryset.select_related('state')
    
    features = []
    for district in queryset:
        properties = {
            'id': district.id,
            'name': district.name,
            'state': district.state.name,
            'population': district.population,
            'literacy_rate': float(district.literacy_rate) if district.literacy_rate else 0
        }
        
        if include_metrics:
            # Add economic indicators
            latest_economic = district.economic_indicators.order_by('-date_recorded').first()
            if latest_economic:
                properties['unemployment_rate'] = float(latest_economic.unemployment_rate) if latest_economic.unemployment_rate else 0
        
        feature = {
            'type': 'Feature',
            'geometry': json.loads(district.geometry.geojson),
            'properties': properties
        }
        features.append(feature)
    
    return {
        'type': 'FeatureCollection',
        'features': features
    }


def export_market_zones_geojson(product_type=None):
    """
    Export market potential zones as GeoJSON for heatmap visualization.
    """
    zones = MarketPotentialZone.objects.select_related('state', 'district')
    
    if product_type:
        zones = zones.filter(product_type=product_type)
    
    features = []
    for zone in zones:
        if zone.district and zone.district.centroid:
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [zone.district.centroid.x, zone.district.centroid.y]
                },
                'properties': {
                    'name': str(zone.district),
                    'state': zone.state.name,
                    'product_type': zone.product_type,
                    'potential_level': zone.potential_level,
                    'market_score': float(zone.market_score),
                    'predicted_reach': float(zone.predicted_reach_percentage) if zone.predicted_reach_percentage else 0
                }
            }
            features.append(feature)
    
    return {
        'type': 'FeatureCollection',
        'features': features
    }


# ==================== LEGACY FUNCTIONS (Keep for backward compatibility) ====================

def get_enhanced_clusters_data():
    """Generate enhanced cluster data - now pulls from database"""
    # Return market zones as clusters
    zones = MarketPotentialZone.objects.select_related('state', 'district').order_by('-market_score')[:10]
    
    clusters = []
    for zone in zones:
        if zone.district and zone.district.centroid:
            level = zone.potential_level.lower()
            clusters.append({
                "lat": zone.district.centroid.y,
                "lng": zone.district.centroid.x,
                "level": level,
                "info": str(zone.district),
                "demographics": {
                    "income": f"₹{zone.district.population or 0:,}",
                    "employment_rate": "N/A",
                    "population_density": str(zone.district.population or 0),
                    "interest_index": str(int(zone.market_score))
                }
            })
    
    # If no zones, return empty list (instead of hardcoded data)
    return clusters


def get_complete_map_config():
    """Complete map configuration for frontend"""
    return {
        "center_lat": 20.5937,
        "center_lng": 78.9629,
        "initial_zoom": 5,
        "max_zoom": 18,
        "geojson_paths": {
            "adm1": "geo/geojson/geoBoundaries-IND-ADM1.geojson",
            "adm2": "geo/geojson/geoBoundaries-IND-ADM2.geojson"
        },
        "zoom_thresholds": {
            "state_to_district": 7,
            "hide_districts": 6
        },
        "map_styles": {
            "boundary_color": "#3388ff",
            "boundary_weight": 2,
            "boundary_opacity": 0.2,
            "hover_color": "yellow"
        }
    }