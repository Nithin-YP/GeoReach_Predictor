import random
import json

def get_enhanced_clusters_data():
    """Generate enhanced cluster data with full demographics"""
    clusters = [
        {
            "lat": 28.6139, 
            "lng": 77.2090, 
            "level": "high", 
            "info": "Delhi",
            "demographics": {
                "income": "₹1,50,000",
                "employment_rate": "85%",
                "population_density": "11,320/km²",
                "interest_index": "78"
            }
        },
        {
            "lat": 19.0760, 
            "lng": 72.8777, 
            "level": "medium", 
            "info": "Mumbai",
            "demographics": {
                "income": "₹1,25,000",
                "employment_rate": "82%",
                "population_density": "20,482/km²",
                "interest_index": "65"
            }
        },
        {
            "lat": 13.0827, 
            "lng": 80.2707, 
            "level": "low", 
            "info": "Chennai",
            "demographics": {
                "income": "₹95,000",
                "employment_rate": "79%",
                "population_density": "26,903/km²",
                "interest_index": "52"
            }
        },
    ]
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