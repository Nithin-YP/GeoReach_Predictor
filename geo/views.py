from django.shortcuts import render
from .utils import (
    get_enhanced_clusters_data, 
    get_complete_map_config,
    get_state_demographics,
    get_district_demographics,
    calculate_region_match_scores
)
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def get_map_context(form_data=None):
    """
    Get map data and configuration for templates
    
    Args:
        form_data: Dictionary with keys: product_type, luxury_level, target_audience, price
    """
    
    # Calculate match scores if form data provided
    match_scores = None
    if form_data and all(k in form_data for k in ['product_type', 'luxury_level', 'target_audience', 'price']):
        try:
            match_scores = calculate_region_match_scores(
                product_type=form_data['product_type'],
                luxury_level=form_data['luxury_level'],
                target_audience=form_data['target_audience'],
                price=form_data['price']
            )
        except Exception as e:
            print(f"Error calculating match scores: {e}")
            match_scores = None
    
    clusters = get_enhanced_clusters_data(match_scores)
    map_config = get_complete_map_config()
    state_demographics = get_state_demographics()
    district_demographics = get_district_demographics()
    
    return {
        'clusters': json.dumps(clusters, cls=DecimalEncoder),
        'map_config': json.dumps(map_config, cls=DecimalEncoder),
        'state_demographics': json.dumps(state_demographics, cls=DecimalEncoder),
        'district_demographics': json.dumps(district_demographics, cls=DecimalEncoder),
        'match_scores': json.dumps(match_scores or {}, cls=DecimalEncoder)
    }

def map_view(request):
    """Standalone map view (if needed separately from entrepreneur dashboard)"""
    context = get_map_context(None)
    return render(request, 'geo/map.html', context)