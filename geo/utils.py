import unicodedata
from django.db import connection
from django.db.models import Avg
from core.models import RegionMetrics, ProductPrediction
from decimal import Decimal

def execute_query(query, params=None):
    """Execute a raw SQL query and return results as list of dicts."""
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        results = []
        for row in cursor.fetchall():
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

def get_region_metrics_for_map(region_type='state'):
    """
    Get region metrics for map visualization
    Returns dict: {region_name: {metrics...}}
    """
    metrics = RegionMetrics.objects.filter(region_type=region_type)
    
    result = {}
    for metric in metrics:
        result[metric.region_name] = {
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
        
        # Also add normalized version of name
        normalized_name = normalize_state_name(metric.region_name)
        result[normalized_name] = result[metric.region_name]
    
    return result

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
            education_weight = 0.2 * luxury_multiplier
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
        else:
            scores[state_name] = 0.0
            scores[normalized_name] = 0.0
    
    return scores

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
    """Returns list of clusters with demographic data from database"""
    
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
    
    # Map states to coordinates
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
                    "employment_rate": f"{float(state['employment_rate']):.2f}",
                    "population_density": f"{int(state['population_density'])}/km²",
                    "unemployment_rate": f"{float(state['est_unemployment_rate']):.2f}"
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