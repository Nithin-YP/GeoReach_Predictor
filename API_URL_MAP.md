# 🗺️ Complete URL Map - GeoReach Predictor

**Project:** GeoReach Predictor  
**Version:** 1.0  
**Last Updated:** October 17, 2025

---

## 📋 Table of Contents

1. [Core Application URLs](#core-application-urls)
2. [GIS Application URLs](#gis-application-urls)
3. [Admin URLs](#admin-urls)
4. [Static & Media URLs](#static--media-urls)
5. [API Summary](#api-summary)

---

## 🎯 Core Application URLs

**Base URL Pattern:** `/core/`

### Authentication Endpoints

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/core/login/` | `core:login` | GET, POST | No | User login page |
| `/core/logout/` | `core:logout` | GET | Yes | User logout |
| `/core/register/entrepreneur/` | `core:entrepreneur_register` | GET, POST | No | Entrepreneur registration |

**Examples:**
```
http://127.0.0.1:8000/core/login/
http://127.0.0.1:8000/core/logout/
http://127.0.0.1:8000/core/register/entrepreneur/
```

---

### Dashboard Endpoints

| URL | Name | Method | Auth Required | Role | Description |
|-----|------|--------|---------------|------|-------------|
| `/core/dashboard/entrepreneur/` | `core:entrepreneur_dashboard` | GET, POST | Yes | Entrepreneur | Entrepreneur dashboard with prediction form |
| `/core/dashboard/admin/` | `core:admin_dashboard` | GET | Yes | Admin | Admin control panel |

**Examples:**
```
http://127.0.0.1:8000/core/dashboard/entrepreneur/
http://127.0.0.1:8000/core/dashboard/admin/
```

---

### Admin Management Endpoints

| URL | Name | Method | Auth Required | Role | Description |
|-----|------|--------|---------------|------|-------------|
| `/core/admin/datasets/` | `core:dataset_management` | GET, POST | Yes | Admin | Dataset upload/management |
| `/core/admin/users/` | `core:user_management` | GET, POST | Yes | Admin | User management (block/unblock) |

**Examples:**
```
http://127.0.0.1:8000/core/admin/datasets/
http://127.0.0.1:8000/core/admin/users/
```

---

### Testing Endpoints

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/core/csrf-test/` | `core:csrf_test` | GET | No | CSRF protection test page |

**Example:**
```
http://127.0.0.1:8000/core/csrf-test/
```

---

## 🗺️ GIS Application URLs

**Base URL Pattern:** `/geo/`

### Map Visualization

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/` | `geo:map` | GET | No | Main interactive map |

**Example:**
```
http://127.0.0.1:8000/geo/
```

---

### State API Endpoints

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/states/` | `geo:api_states` | GET | No | List all states (JSON) |
| `/geo/api/states/<int:state_id>/` | `geo:api_state_detail` | GET | No | Single state details |
| `/geo/api/states/geojson/` | `geo:api_states_geojson` | GET | No | All states as GeoJSON |
| `/geo/api/states/<int:state_id>/geojson/` | `geo:api_state_geojson` | GET | No | Single state as GeoJSON |

**Examples:**
```
http://127.0.0.1:8000/geo/api/states/
http://127.0.0.1:8000/geo/api/states/1/
http://127.0.0.1:8000/geo/api/states/geojson/
http://127.0.0.1:8000/geo/api/states/1/geojson/
```

**Response Format (JSON):**
```json
{
  "id": 1,
  "name": "Maharashtra",
  "code": "MH",
  "population": 112374333,
  "area_km2": 307713.0,
  "population_density": 365.23,
  "districts_count": 36
}
```

**Response Format (GeoJSON):**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": 1,
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": [[[[72.xxx, 19.xxx], ...]]]
      },
      "properties": {
        "name": "Maharashtra",
        "population": 112374333,
        "area_km2": 307713.0
      }
    }
  ]
}
```

---

### District API Endpoints

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/districts/` | `geo:api_districts` | GET | No | List all districts (JSON) |
| `/geo/api/districts/<int:district_id>/` | `geo:api_district_detail` | GET | No | Single district details |
| `/geo/api/districts/geojson/` | `geo:api_districts_geojson` | GET | No | All districts as GeoJSON |
| `/geo/api/districts/<int:district_id>/geojson/` | `geo:api_district_geojson` | GET | No | Single district as GeoJSON |

**Query Parameters:**
- `state_id` - Filter districts by state
- `min_population` - Filter by minimum population
- `max_population` - Filter by maximum population

**Examples:**
```
http://127.0.0.1:8000/geo/api/districts/
http://127.0.0.1:8000/geo/api/districts/?state_id=1
http://127.0.0.1:8000/geo/api/districts/1/
http://127.0.0.1:8000/geo/api/districts/geojson/
http://127.0.0.1:8000/geo/api/districts/1/geojson/
```

**Response Format (JSON):**
```json
{
  "id": 1,
  "name": "Mumbai",
  "state": "Maharashtra",
  "state_id": 1,
  "population": 12442373,
  "literacy_rate": 89.21,
  "area_km2": 603.4
}
```

---

### Economic Indicators API

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/economic-indicators/` | `geo:api_economic_indicators` | GET | No | Economic data by region |
| `/geo/api/economic-indicators/<int:id>/` | `geo:api_economic_indicator_detail` | GET | No | Single indicator details |

**Query Parameters:**
- `state_id` - Filter by state
- `district_id` - Filter by district
- `area_type` - Filter by area type (RURAL, URBAN, COMBINED)
- `year` - Filter by year

**Examples:**
```
http://127.0.0.1:8000/geo/api/economic-indicators/
http://127.0.0.1:8000/geo/api/economic-indicators/?state_id=1
http://127.0.0.1:8000/geo/api/economic-indicators/?area_type=URBAN
http://127.0.0.1:8000/geo/api/economic-indicators/1/
```

**Response Format:**
```json
{
  "id": 1,
  "state": "Maharashtra",
  "district": "Mumbai",
  "area_type": "URBAN",
  "unemployment_rate": 4.5,
  "employment_rate": 95.5,
  "avg_monthly_salary": 45000.0,
  "date_recorded": "2024-01-01"
}
```

---

### Demographic Profiles API

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/demographics/` | `geo:api_demographics` | GET | No | Demographic profiles |
| `/geo/api/demographics/<int:id>/` | `geo:api_demographic_detail` | GET | No | Single profile details |

**Query Parameters:**
- `state_id` - Filter by state
- `district_id` - Filter by district
- `age_group` - Filter by age group
- `city_tier` - Filter by city tier
- `education_level` - Filter by education

**Examples:**
```
http://127.0.0.1:8000/geo/api/demographics/
http://127.0.0.1:8000/geo/api/demographics/?age_group=25-34
http://127.0.0.1:8000/geo/api/demographics/?city_tier=TIER_1
http://127.0.0.1:8000/geo/api/demographics/1/
```

**Response Format:**
```json
{
  "id": 1,
  "state": "Maharashtra",
  "district": "Mumbai",
  "age_group": "25-34",
  "education_level": "BACHELOR",
  "city_tier": "TIER_1",
  "avg_income": 60000.0,
  "avg_spending": 45000.0,
  "groceries_expenditure": 8000.0,
  "transport_expenditure": 5000.0
}
```

---

### Industry Employment API

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/industry-employment/` | `geo:api_industry_employment` | GET | No | Industry employment data |
| `/geo/api/industry-employment/<int:id>/` | `geo:api_industry_employment_detail` | GET | No | Single record details |

**Query Parameters:**
- `state_id` - Filter by state
- `industry` - Filter by industry type

**Examples:**
```
http://127.0.0.1:8000/geo/api/industry-employment/
http://127.0.0.1:8000/geo/api/industry-employment/?industry=TECHNOLOGY
http://127.0.0.1:8000/geo/api/industry-employment/1/
```

**Response Format:**
```json
{
  "id": 1,
  "state": "Maharashtra",
  "district": "Pune",
  "industry": "TECHNOLOGY",
  "employed_count": 250000,
  "unemployed_count": 5000,
  "avg_salary": 80000.0
}
```

---

### Market Potential Zones API

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/market-zones/` | `geo:api_market_zones` | GET | Yes | Market potential zones |
| `/geo/api/market-zones/<int:id>/` | `geo:api_market_zone_detail` | GET | Yes | Single zone details |

**Query Parameters:**
- `product_type` - Filter by product
- `potential_level` - Filter by level (HIGH, MEDIUM, LOW)
- `state_id` - Filter by state

**Examples:**
```
http://127.0.0.1:8000/geo/api/market-zones/
http://127.0.0.1:8000/geo/api/market-zones/?potential_level=HIGH
http://127.0.0.1:8000/geo/api/market-zones/1/
```

**Response Format:**
```json
{
  "id": 1,
  "state": "Maharashtra",
  "district": "Mumbai",
  "product_type": "Premium Smartphone",
  "potential_level": "HIGH",
  "market_score": 85.5,
  "predicted_reach_percentage": 45.2,
  "estimated_target_population": 2500000
}
```

---

### Spatial Query Endpoints

| URL | Name | Method | Auth Required | Description |
|-----|------|--------|---------------|-------------|
| `/geo/api/nearby-districts/` | `geo:api_nearby_districts` | GET | No | Districts within radius |
| `/geo/api/corridor-analysis/` | `geo:api_analyze_corridor` | POST | No | Market analysis along corridor |
| `/geo/api/market-reach-analysis/` | `geo:api_market_reach_analysis` | GET | Yes | Comprehensive market analysis |

**Nearby Districts Parameters:**
- `lat` - Latitude (required)
- `lng` - Longitude (required)
- `radius_km` - Radius in kilometers (default: 50)

**Example:**
```
http://127.0.0.1:8000/geo/api/nearby-districts/?lat=19.0760&lng=72.8777&radius_km=50
```

**Response:**
```json
{
  "center": {
    "lat": 19.0760,
    "lng": 72.8777
  },
  "radius_km": 50,
  "districts": [
    {
      "id": 1,
      "name": "Mumbai",
      "distance_km": 0,
      "population": 12442373
    },
    {
      "id": 2,
      "name": "Thane",
      "distance_km": 25.3,
      "population": 8829665
    }
  ],
  "count": 2
}
```

---

**Corridor Analysis Parameters (POST):**
```json
{
  "start_lat": 19.0760,
  "start_lng": 72.8777,
  "end_lat": 18.5204,
  "end_lng": 73.8567,
  "buffer_km": 20
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/geo/api/corridor-analysis/ \
  -H "Content-Type: application/json" \
  -d '{
    "start_lat": 19.0760,
    "start_lng": 72.8777,
    "end_lat": 18.5204,
    "end_lng": 73.8567,
    "buffer_km": 20
  }'
```

**Response:**
```json
{
  "start": {"lat": 19.0760, "lng": 72.8777},
  "end": {"lat": 18.5204, "lng": 73.8567},
  "buffer_km": 20,
  "distance_km": 118.5,
  "districts_along_route": [
    {"name": "Mumbai", "population": 12442373},
    {"name": "Raigad", "population": 2634200},
    {"name": "Pune", "population": 9426959}
  ],
  "total_population": 24503532,
  "market_potential": "HIGH"
}
```

---

## 🔧 Admin URLs

**Base URL Pattern:** `/admin/`

| URL | Description |
|-----|-------------|
| `/admin/` | Django admin login |
| `/admin/core/user/` | User management |
| `/admin/geo/state/` | State management |
| `/admin/geo/district/` | District management |
| `/admin/geo/economicindicator/` | Economic indicators |
| `/admin/geo/demographicprofile/` | Demographics |
| `/admin/geo/industryemployment/` | Industry data |
| `/admin/geo/marketpotentialzone/` | Market zones |
| `/admin/geo/spatialquery/` | Spatial query logs |

**Examples:**
```
http://127.0.0.1:8000/admin/
http://127.0.0.1:8000/admin/core/user/
http://127.0.0.1:8000/admin/geo/state/
```

---

## 📦 Static & Media URLs

| URL Pattern | Description |
|-------------|-------------|
| `/static/` | Static files (CSS, JS, images) |
| `/media/` | User-uploaded files |
| `/static/geo/js/map.js` | Map initialization script |
| `/static/geo/js/csrf.js` | CSRF utility |
| `/static/admin/` | Django admin static files |

**Examples:**
```
http://127.0.0.1:8000/static/geo/js/map.js
http://127.0.0.1:8000/static/geo/js/csrf.js
http://127.0.0.1:8000/media/datasets/uploaded_file.csv
```

---

## 📊 API Summary

### RESTful Endpoints Count

| Category | GET Endpoints | POST Endpoints | Total |
|----------|---------------|----------------|-------|
| States | 4 | 0 | 4 |
| Districts | 4 | 0 | 4 |
| Economic Indicators | 2 | 0 | 2 |
| Demographics | 2 | 0 | 2 |
| Industry Employment | 2 | 0 | 2 |
| Market Zones | 2 | 0 | 2 |
| Spatial Queries | 2 | 1 | 3 |
| **Total GIS APIs** | **18** | **1** | **19** |
| Core/Auth | 3 | 3 | 6 |
| Dashboards | 2 | 1 | 3 |
| Admin | 2 | 2 | 4 |
| **Grand Total** | **25** | **7** | **32** |

---

## 🔍 Query Parameter Reference

### Common Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `state_id` | Integer | Filter by state ID | `?state_id=1` |
| `district_id` | Integer | Filter by district ID | `?district_id=5` |
| `lat` | Float | Latitude | `?lat=19.0760` |
| `lng` | Float | Longitude | `?lng=72.8777` |
| `radius_km` | Float | Radius in km | `?radius_km=50` |

### Demographics Parameters

| Parameter | Type | Values | Example |
|-----------|------|--------|---------|
| `age_group` | String | 18-24, 25-34, 35-44, 45-54, 55+ | `?age_group=25-34` |
| `city_tier` | String | TIER_1, TIER_2, TIER_3 | `?city_tier=TIER_1` |
| `education_level` | String | HIGH_SCHOOL, BACHELOR, MASTER, PHD | `?education_level=BACHELOR` |

### Economic Indicators Parameters

| Parameter | Type | Values | Example |
|-----------|------|--------|---------|
| `area_type` | String | RURAL, URBAN, COMBINED | `?area_type=URBAN` |
| `year` | Integer | Any year | `?year=2024` |

### Industry Parameters

| Parameter | Type | Values |
|-----------|------|--------|
| `industry` | String | RETAIL, HOSPITALITY, TECHNOLOGY, HEALTHCARE, EDUCATION, MANUFACTURING, FINANCE, AGRICULTURE, CONSTRUCTION, OTHER |

---

## 🧪 Testing URLs

Run these commands to test all endpoints:

```bash
# Test state APIs
curl http://127.0.0.1:8000/geo/api/states/
curl http://127.0.0.1:8000/geo/api/states/1/
curl http://127.0.0.1:8000/geo/api/states/geojson/

# Test district APIs
curl http://127.0.0.1:8000/geo/api/districts/
curl http://127.0.0.1:8000/geo/api/districts/1/
curl http://127.0.0.1:8000/geo/api/districts/geojson/

# Test spatial queries
curl "http://127.0.0.1:8000/geo/api/nearby-districts/?lat=19.0760&lng=72.8777&radius_km=50"

# Test corridor analysis (requires CSRF token or exemption)
curl -X POST http://127.0.0.1:8000/geo/api/corridor-analysis/ \
  -H "Content-Type: application/json" \
  -d '{"start_lat":19.0760,"start_lng":72.8777,"end_lat":18.5204,"end_lng":73.8567,"buffer_km":20}'
```

---

## 📝 URL Naming Conventions

### Pattern Format
- **App Namespace:** `app_name:url_name`
- **Example:** `geo:api_states`, `core:login`

### Naming Convention
- List views: `api_<model_plural>`
- Detail views: `api_<model>_detail`
- GeoJSON views: `api_<model_plural>_geojson`
- Actions: `<action>_<model>`

**Examples:**
- `geo:api_states` - List all states
- `geo:api_state_detail` - Single state
- `geo:api_states_geojson` - States as GeoJSON
- `core:entrepreneur_register` - Registration action

---

## 🔗 URL Reversing

### In Python Views
```python
from django.urls import reverse

# Get URL
url = reverse('geo:api_states')
# Returns: /geo/api/states/

# With parameters
url = reverse('geo:api_state_detail', args=[1])
# Returns: /geo/api/states/1/
```

### In Templates
```html
{% url 'geo:map' %}
{% url 'geo:api_state_detail' state.id %}
{% url 'core:entrepreneur_dashboard' %}
```

### In JavaScript
```javascript
// Using string interpolation
const url = `/geo/api/states/${stateId}/geojson/`;

// Fetch data
fetch(url)
  .then(response => response.json())
  .then(data => console.log(data));
```

---

**Last Updated:** October 17, 2025  
**Total Endpoints:** 32  
**API Version:** 1.0
