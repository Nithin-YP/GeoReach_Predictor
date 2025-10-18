from django.shortcuts import render
from .utils import (
    get_enhanced_clusters_data, 
    get_complete_map_config,
    get_state_demographics,
    get_district_demographics,
    calculate_region_match_scores,
    get_region_metrics_for_map,
    calculate_and_store_match_scores
)
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
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
    """
    
    # If form data provided, calculate and store predictions
    if user and form_data and all(k in form_data for k in ['product_type', 'luxury_level', 'target_audience', 'price']):
        try:
            calculate_and_store_match_scores(
                user=user,
                product_type=form_data['product_type'],
                luxury_level=form_data['luxury_level'],
                target_audience=form_data['target_audience'],
                price=form_data['price']
            )
        except Exception as e:
            print(f"Error calculating match scores: {e}")
    
    # Get precomputed metrics from database
    state_metrics = get_region_metrics_for_map('state')
    district_metrics = get_region_metrics_for_map('district')
    
    # Extract match scores for backward compatibility
    match_scores = {}
    for name, metrics in state_metrics.items():
        if metrics['avg_predicted_success'] is not None:
            match_scores[name] = metrics['avg_predicted_success'] * 100
    
    # Get clusters (empty for now - will be populated by ML)
    clusters = get_enhanced_clusters_data(match_scores)
    
    map_config = get_complete_map_config()
    
    return {
        'map_config': json.dumps(map_config, cls=DecimalEncoder),
        'clusters': json.dumps(clusters, cls=DecimalEncoder),
        'state_demographics': json.dumps(state_metrics, cls=DecimalEncoder),  # Changed from state_metrics
        'district_demographics': json.dumps(district_metrics, cls=DecimalEncoder),  # Changed from district_metrics
        'match_scores': json.dumps(match_scores, cls=DecimalEncoder)
    }

def map_view(request):
    """Standalone map view (if needed separately from entrepreneur dashboard)"""
    context = get_map_context(None)
    return render(request, 'geo/map.html', context)