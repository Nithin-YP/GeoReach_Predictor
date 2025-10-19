"""
Test script for PostGIS API endpoints
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(name, url):
    """Test a single API endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print('='*60)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, dict):
                print(f"Response keys: {list(data.keys())}")
                if 'features' in data:
                    print(f"Number of features: {len(data['features'])}")
                    if data['features']:
                        print(f"First feature sample: {json.dumps(data['features'][0], indent=2)[:500]}...")
                else:
                    print(f"Response: {json.dumps(data, indent=2)[:500]}...")
            elif isinstance(data, list):
                print(f"Number of items: {len(data)}")
                if data:
                    print(f"First item: {json.dumps(data[0], indent=2)[:500]}...")
            else:
                print(f"Response: {data}")
        else:
            print(f"Error: {response.text[:500]}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

# Test all endpoints
print("\n" + "="*60)
print("TESTING POSTGIS API ENDPOINTS")
print("="*60)

# 1. States GeoJSON
test_endpoint(
    "States GeoJSON",
    f"{BASE_URL}/geo/api/states/geojson/"
)

# 2. Districts GeoJSON
test_endpoint(
    "Districts GeoJSON",
    f"{BASE_URL}/geo/api/districts/geojson/"
)

# 3. Market Zones
test_endpoint(
    "Market Potential Zones",
    f"{BASE_URL}/geo/api/market-zones/"
)

# 4. Nearby Districts (using Mumbai coordinates as example)
test_endpoint(
    "Nearby Districts (Mumbai, 100km radius)",
    f"{BASE_URL}/geo/api/districts/nearby/?lat=19.0760&lng=72.8777&radius=100"
)

# 5. Point Location (Mumbai)
test_endpoint(
    "Point Location (Mumbai)",
    f"{BASE_URL}/geo/api/point-location/?lat=19.0760&lng=72.8777"
)

# 6. Demographic Heatmap (CORRECTED PARAMETERS)
test_endpoint(
    "Demographic Heatmap (18-24, TIER_1)",
    f"{BASE_URL}/geo/api/demographic-heatmap/?age_group=18-24&city_tier=TIER_1"
)

# 7. Employment Hotspots (with industry that has data)
test_endpoint(
    "Employment Hotspots (IT industry)",
    f"{BASE_URL}/geo/api/employment-hotspots/?industry=Information Technology&min_employed=50000"
)

print("\n" + "="*60)
print("TESTING COMPLETED")
print("="*60)
