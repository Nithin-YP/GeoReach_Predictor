from django.contrib.gis.geos import Point, GEOSGeometry, LineString
from django.contrib.gis.measure import D  # Distance
from django.contrib.gis.db.models.functions import Distance, Area
from django.db.models import Avg, Sum, Count, Q, F
from .models import (State, District, EconomicIndicator, DemographicProfile, 
                     IndustryEmployment, MarketPotentialZone)
import json
import unicodedata
from django.db import connection
from core.models import RegionMetrics, ProductPrediction
from decimal import Decimal


# ==================== UTILITY FUNCTIONS ====================

def execute_query(query, params=None):
    """Execute a raw SQL query and return results as list of dicts."""
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        # If the query does not return rows (e.g., INSERT/UPDATE/DELETE), description will be None
        if cursor.description is None:
            return []
        columns = [col[0] for col in cursor.description]
        results = []
        rows = cursor.fetchall()
        for row in rows:
            row_dict = {}
            for col, val in zip(columns, row):
                if isinstance(val, Decimal):
                    row_dict[col] = float(val)
                else:
                    row_dict[col] = val
            results.append(row_dict)
        return results


def normalize_state_name(name):
    """Normalize state names by removing diacritics and special characters"""
    if not name:
        return name
    # Remove accents/diacritics (ā → a, ī → i, etc.)
    normalized = unicodedata.normalize('NFD', name)
    without_diacritics = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
    return without_diacritics.strip()


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


# ==================== PREDICTION & SCORING ====================

def calculate_and_store_match_scores(user, product_type, luxury_level, target_audience, price):
    """
    Calculate match scores and store them in ProductPrediction and RegionMetrics
    """
    # Get all states
    states = RegionMetrics.objects.filter(region_type='state')
    
    luxury_multiplier = {
        'Basic': 0.5,
        'Standard': 1.0,
        'Premium': 1.5,
        'Luxury': 2.0
    }.get(luxury_level, 1.0)
    
    min_income = price * 10 * luxury_multiplier
    max_income = price * 50 * luxury_multiplier
    
    predictions = []
    
    for state_metric in states:
        score = 0.0
        factors = 0
        feature_importance = {}
        
        # Factor 1: Income match (40% weight)
        if state_metric.avg_income:
            avg_income = float(state_metric.avg_income)
            if min_income <= avg_income <= max_income:
                income_score = 100
            elif avg_income > max_income:
                income_score = 80
            else:
                income_score = max(0, (avg_income / min_income) * 60)
            
            score += income_score * 0.4
            factors += 0.4
            feature_importance['income'] = round(income_score * 0.4 / 100, 2)
        
        # Factor 2: Employment rate (20% weight)
        if state_metric.employment_rate:
            employment_score = float(state_metric.employment_rate)
            score += employment_score * 0.2
            factors += 0.2
            feature_importance['employment'] = round(employment_score * 0.2 / 100, 2)
        
        # Factor 3: Literacy (20% weight)
        if state_metric.literacy_rate:
            literacy_score = float(state_metric.literacy_rate)
            score += literacy_score * 0.2
            factors += 0.2
            feature_importance['education'] = round(literacy_score * 0.2 / 100, 2)
        
        # Factor 4: Population density / market size (20% weight)
        if state_metric.population_density:
            density_score = min(100, float(state_metric.population_density) / 10)
            score += density_score * 0.2
            factors += 0.2
            feature_importance['market_size'] = round(density_score * 0.2 / 100, 2)
        
        # Normalize
        final_score = (score / factors) if factors > 0 else 0
        predicted_success = final_score / 100  # Convert to 0-1
        
        # Store prediction
        prediction = ProductPrediction.objects.create(
            user=user,
            product_type=product_type,
            luxury_level=luxury_level,
            target_audience=target_audience,
            price=price,
            region_type='state',
            region_id=state_metric.region_id,
            region_name=state_metric.region_name,
            predicted_success=predicted_success,
            predicted_reach=predicted_success * 0.8,  # Simple estimate
            confidence=0.7 if factors >= 3 else 0.5,
            feature_importance=feature_importance,
            model_version='business_rules_v1.0'
        )
        predictions.append(prediction)
    
    # Update RegionMetrics with aggregated predictions
    for state_metric in states:
        avg_pred = ProductPrediction.objects.filter(
            region_type='state',
            region_id=state_metric.region_id
        ).aggregate(Avg('predicted_success'))['predicted_success__avg']
        
        if avg_pred:
            state_metric.avg_predicted_success = avg_pred
            state_metric.model_version = 'business_rules_v1.0'
            state_metric.save()
    
    return predictions


def calculate_region_match_scores(product_type, luxury_level, target_audience, price):
    """
    Calculate match scores for each state based on prediction inputs.
    Returns dict: {state_name: match_score_percentage}
    """
    scores = {}
    
    # Normalize luxury level to a multiplier (Basic=0.5, Standard=1.0, Premium=1.5, Luxury=2.0)
    luxury_multiplier = {
        'Basic': 0.5,
        'Standard': 1.0,
        'Premium': 1.5,
        'Luxury': 2.0
    }.get(luxury_level, 1.0)
    
    # Calculate expected income range based on price and luxury level
    min_income = price * 10 * luxury_multiplier  # Customers should earn 10x+ the price
    max_income = price * 50 * luxury_multiplier
    
    # Query: Get average income and spending by state (from customers table)
    query = """
        SELECT 
            c.location as state_name,
            AVG(c.income) as avg_income,
            AVG(c.spending) as avg_spending,
            COUNT(*) as customer_count
        FROM customers c
        WHERE c.location IS NOT NULL
        AND c.income IS NOT NULL
        GROUP BY c.location
    """
    customer_data = execute_query(query)
    customer_by_state = {row['state_name']: row for row in customer_data}
    
    # Query: Get employment and education data by state
    query = """
        SELECT 
            e.location as state_name,
            AVG(e.monthly_salary_inr) as avg_salary,
            COUNT(CASE WHEN e.employment_status = 'Employed' THEN 1 END) as employed_count,
            COUNT(*) as total_count,
            COUNT(CASE WHEN e.education_level IN ('Bachelors', 'Masters', 'Ph.D') THEN 1 END) as educated_count
        FROM employment e
        WHERE e.location IS NOT NULL
        GROUP BY e.location
    """
    employment_data = execute_query(query)
    employment_by_state = {row['state_name']: row for row in employment_data}
    
    # Query: Get expenditure patterns by city tier (map to states later)
    query = """
        SELECT 
            city_tier,
            AVG(disposable_income) as avg_disposable,
            AVG(entertainment_exp + eating_out_exp) as avg_discretionary
        FROM expenditures
        WHERE city_tier IS NOT NULL
        GROUP BY city_tier
    """
    expenditure_data = execute_query(query)
    expenditure_by_tier = {row['city_tier']: row for row in expenditure_data}
    
    # Get all states from database
    query = """
        SELECT 
            state_name,
            population,
            area_type,
            est_unemployment_rate
        FROM states
        WHERE state_name IS NOT NULL
    """
    all_states = execute_query(query)
    
    # Calculate match score for each state
    for state in all_states:
        state_name = state['state_name']
        normalized_name = normalize_state_name(state_name)
        score = 0.0
        factors = 0
        
        # Factor 1: Income match (40% weight)
        customer_info = customer_by_state.get(state_name)
        if customer_info:
            avg_income = customer_info['avg_income']
            if min_income <= avg_income <= max_income:
                income_score = 100
            elif avg_income > max_income:
                # Too rich, might still buy but score slightly lower
                income_score = 80
            elif avg_income < min_income:
                # Calculate partial score based on how close they are
                income_score = max(0, (avg_income / min_income) * 60)
            else:
                income_score = 50
            score += income_score * 0.4
            factors += 0.4
        
        # Factor 2: Employment rate (20% weight)
        employment_info = employment_by_state.get(state_name)
        if employment_info and employment_info['total_count'] > 0:
            employment_rate = (employment_info['employed_count'] / employment_info['total_count']) * 100
            score += employment_rate * 0.2
            factors += 0.2
        
        # Factor 3: Education level (20% weight) - higher for premium/luxury products
        if employment_info and employment_info['total_count'] > 0:
            education_rate = (employment_info['educated_count'] / employment_info['total_count']) * 100
            score += education_rate * 0.2
            factors += 0.2
        
        # Factor 4: Area type preference (10% weight)
        area_type = state['area_type']
        if area_type == 'Urban' and luxury_level in ['Premium', 'Luxury']:
            score += 90 * 0.1
            factors += 0.1
        elif area_type == 'Rural' and luxury_level in ['Basic', 'Standard']:
            score += 70 * 0.1
            factors += 0.1
        elif area_type:
            score += 50 * 0.1
            factors += 0.1
        
        # Factor 5: Population size (10% weight) - larger market opportunity
        if state['population']:
            pop_score = min(100, (state['population'] / 100000000) * 100)  # Normalize to 100M
            score += pop_score * 0.1
            factors += 0.1
        
        # Normalize score
        if factors > 0:
            final_score = (score / factors) if factors < 1 else score
            scores[state_name] = round(final_score, 2)
            scores[normalized_name] = round(final_score, 2)
        else:
            scores[state_name] = 0.0
            scores[normalized_name] = 0.0
    
    return scores


def get_region_metrics_for_map(region_type='state'):
    """
    Get region metrics for map visualization
    Returns dict: {region_name: {metrics...}}
    """
    metrics = RegionMetrics.objects.filter(region_type=region_type)
    
    result = {}
    for metric in metrics:
        metric_data = {
            'region_id': metric.region_id,
            'avg_predicted_success': float(metric.avg_predicted_success) if metric.avg_predicted_success else None,
            'avg_predicted_reach': float(metric.avg_predicted_reach) if metric.avg_predicted_reach else None,
            'confidence_score': float(metric.confidence_score) if metric.confidence_score else None,
            'spending_index': float(metric.spending_index) if metric.spending_index else None,
            'avg_income': float(metric.avg_income) if metric.avg_income else None,
            'avg_spending': float(metric.avg_spending) if metric.avg_spending else None,
            'population_density': float(metric.population_density) if metric.population_density else None,
            'literacy_rate': float(metric.literacy_rate) if metric.literacy_rate else None,
            'employment_rate': float(metric.employment_rate) if metric.employment_rate else None,
            'data_coverage': float(metric.data_coverage) if metric.data_coverage else None,
            'top_drivers': metric.top_drivers,
        }
        
        # Store with both original and normalized names
        result[metric.region_name] = metric_data
        normalized_name = normalize_state_name(metric.region_name)
        result[normalized_name] = metric_data
    
    return result


def get_state_demographics():
    """Get demographic data for all states"""
    query = """
        SELECT 
            state_name,
            population,
            population_density,
            est_unemployment_rate,
            est_employed,
            area_type,
            ROUND((est_employed::numeric / NULLIF(population, 0)::numeric * 100), 2) as employment_rate
        FROM states 
        WHERE state_name IS NOT NULL
    """
    states_data = execute_query(query)
    
    # Convert to dictionary with BOTH original and normalized names as keys
    result = {}
    for row in states_data:
        original_name = row['state_name']
        normalized_name = normalize_state_name(original_name)
        result[original_name] = row
        result[normalized_name] = row  # Allows lookup by normalized name
    
    return result


def get_district_demographics():
    """Get demographic data for all districts with entrepreneur-relevant metrics"""
    query = """
        SELECT 
            d.district_name,
            s.state_name,
            d.population_district,
            d.literacy_rate,
            s.area_type,
            s.population_density,
            s.est_unemployment_rate,
            ROUND((s.est_employed::numeric / NULLIF(s.population, 0)::numeric * 100), 2) as employment_rate
        FROM districts d
        LEFT JOIN states s ON d.state_id = s.state_id
        WHERE d.district_name IS NOT NULL
    """
    districts_data = execute_query(query)
    
    # Get average income by location from customers table
    income_query = """
        SELECT 
            location,
            AVG(income) as avg_income,
            AVG(spending) as avg_spending
        FROM customers
        WHERE location IS NOT NULL
        GROUP BY location
    """
    income_data = execute_query(income_query)
    income_by_location = {row['location']: row for row in income_data}
    
    # Combine data
    result = {}
    for row in districts_data:
        original_name = row['district_name']
        normalized_name = normalize_state_name(original_name)
        state_name = row['state_name']
        
        # Add income data if available for the state
        if state_name and state_name in income_by_location:
            row['avg_income'] = income_by_location[state_name]['avg_income']
            row['avg_spending'] = income_by_location[state_name]['avg_spending']
        else:
            row['avg_income'] = None
            row['avg_spending'] = None
        
        result[original_name] = row
        result[normalized_name] = row 
    
    return result


def get_enhanced_clusters_data(match_scores=None):
    """
    Returns list of clusters with demographic data from database.
    Can optionally use match_scores to highlight regions.
    """
    # Get top employment states for high-level clusters
    query = """
        SELECT 
            state_name,
            population,
            population_density,
            ROUND((est_employed::numeric / NULLIF(population, 0)::numeric * 100), 2) as employment_rate,
            est_unemployment_rate
        FROM states 
        WHERE state_name IS NOT NULL
        AND population > 0
        AND est_employed IS NOT NULL
        ORDER BY employment_rate DESC
        LIMIT 10
    """
    top_states = execute_query(query)
    
    # Map states to coordinates (major cities as reference points)
    state_coords = {
        'Delhi': {'lat': 28.7041, 'lng': 77.1025},
        'Maharashtra': {'lat': 19.0760, 'lng': 72.8777},
        'Karnataka': {'lat': 12.9716, 'lng': 77.5946},
        'Tamil Nadu': {'lat': 13.0827, 'lng': 80.2707},
        'Gujarat': {'lat': 23.0225, 'lng': 72.5714},
        'West Bengal': {'lat': 22.5726, 'lng': 88.3639},
        'Uttar Pradesh': {'lat': 26.8467, 'lng': 80.9462},
        'Rajasthan': {'lat': 26.9124, 'lng': 75.7873},
        'Madhya Pradesh': {'lat': 23.2599, 'lng': 77.4126},
        'Telangana': {'lat': 17.3850, 'lng': 78.4867},
        'Andhra Pradesh': {'lat': 15.9129, 'lng': 79.7400},
        'Punjab': {'lat': 31.1471, 'lng': 75.3412},
        'Haryana': {'lat': 29.0588, 'lng': 76.0856},
        'Kerala': {'lat': 10.8505, 'lng': 76.2711},
        'Odisha': {'lat': 20.9517, 'lng': 85.0985},
        'Jharkhand': {'lat': 23.6102, 'lng': 85.2799},
        'Assam': {'lat': 26.2006, 'lng': 92.9376},
        'Bihar': {'lat': 25.0961, 'lng': 85.3131},
        'Chhattisgarh': {'lat': 21.2787, 'lng': 81.8661},
        'Goa': {'lat': 15.2993, 'lng': 74.1240}
    }
    
    clusters = []
    for state in top_states:
        state_name = state['state_name']
        coords = state_coords.get(state_name)
        
        if coords:
            # Use match score if provided, otherwise use employment rate
            if match_scores and state_name in match_scores:
                score = match_scores[state_name]
            else:
                score = float(state['employment_rate'] or 0)
            
            # Determine level based on score
            if score >= 70:
                level = 'high'
            elif score >= 50:
                level = 'medium'
            else:
                level = 'low'
            
            clusters.append({
                "lat": coords['lat'],
                "lng": coords['lng'],
                "level": level,
                "info": state_name,
                "match_score": score,
                "demographics": {
                    "population": f"{int(state['population']):,}",
                    "employment_rate": f"{float(state['employment_rate']):.2f}%",
                    "population_density": f"{int(state['population_density'])}/km²",
                    "unemployment_rate": f"{float(state['est_unemployment_rate']):.2f}%"
                }
            })
    
    return clusters


def get_complete_map_config():
    """Returns complete map configuration"""
    return {
        "center_lat": 20.5937,
        "center_lng": 78.9629,
        "initial_zoom": 5,
        "max_zoom": 18,
        "zoom_thresholds": {
            "state_to_district": 7
        },
        "geojson_paths": {
            "adm1": "geo/geojson/geoBoundaries-IND-ADM1.geojson",
            "adm2": "geo/geojson/geoBoundaries-IND-ADM2.geojson"
        }
    }