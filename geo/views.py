from django.shortcuts import render
from .utils import get_enhanced_clusters_data, get_complete_map_config
import json

def get_map_context(request_params=None):
    """Generate context data for map visualization"""
    clusters = get_enhanced_clusters_data()
    config = get_complete_map_config()
    
    return {
        'clusters': json.dumps(clusters),
        'map_config': json.dumps(config),
    }

def map_view(request, context=None):
    """Standalone map view"""
    if context is None:
        context = {}
    
    map_context = get_map_context()
    context.update(map_context)
    
    return render(request, "geo/map.html", context)