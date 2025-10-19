# 🗺️ PostGIS Spatial Queries Guide

**Project:** GeoReach Predictor  
**Purpose:** Complete reference for all PostGIS spatial queries  
**Last Updated:** October 17, 2025

---

## 📋 Table of Contents

1. [Introduction to PostGIS](#introduction-to-postgis)
2. [Basic Spatial Queries](#basic-spatial-queries)
3. [Point Operations](#point-operations)
4. [Polygon Operations](#polygon-operations)
5. [Distance & Proximity](#distance--proximity)
6. [Spatial Relationships](#spatial-relationships)
7. [Advanced Queries](#advanced-queries)
8. [Performance Optimization](#performance-optimization)
9. [Real-World Examples](#real-world-examples)

---

## 🎯 Introduction to PostGIS

### What is PostGIS?

PostGIS is a spatial database extender for PostgreSQL. It adds support for:
- Geographic objects (points, lines, polygons)
- Spatial indexing (GiST)
- Spatial functions (distance, contains, intersects, etc.)
- Coordinate systems (SRID)

### Our Setup

- **Database:** PostgreSQL 14+
- **Extension:** PostGIS 3.3+
- **SRID:** 4326 (WGS84 - Geographic coordinates)
- **Geometry Types:** Point, MultiPolygon

**Models Using PostGIS:**
- `State` - MultiPolygon boundaries
- `District` - MultiPolygon boundaries
- Both have Point centroids

---

## 🔍 Basic Spatial Queries

### 1. Check PostGIS Version

```sql
-- SQL
SELECT PostGIS_Version();
```

```python
# Python (Django)
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT PostGIS_Version()")
    version = cursor.fetchone()[0]
    print(f"PostGIS Version: {version}")
```

**Output:** `3.3.0`

---

### 2. Get Geometry Type

```sql
-- SQL
SELECT 
    name,
    ST_GeometryType(geometry) as geom_type
FROM geo_state
LIMIT 5;
```

```python
# Python
from geo.models import State

states = State.objects.all()[:5]
for state in states:
    print(f"{state.name}: {state.geometry.geom_type}")
```

**Output:**
```
Maharashtra: MultiPolygon
Uttar Pradesh: MultiPolygon
Tamil Nadu: MultiPolygon
```

---

### 3. Get SRID (Coordinate System)

```sql
-- SQL
SELECT 
    name,
    ST_SRID(geometry) as srid
FROM geo_state
LIMIT 1;
```

```python
# Python
state = State.objects.first()
print(f"SRID: {state.geometry.srid}")
```

**Output:** `4326` (WGS84 - latitude/longitude)

---

## 📍 Point Operations

### 1. Create a Point

```python
from django.contrib.gis.geos import Point

# Mumbai coordinates
mumbai_point = Point(72.8777, 19.0760, srid=4326)
# Format: Point(longitude, latitude, srid)
```

**Note:** PostGIS uses (longitude, latitude) order, not (lat, lng)!

---

### 2. Find Which State Contains a Point

```sql
-- SQL (Mumbai coordinates)
SELECT 
    name
FROM geo_state
WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326));
```

```python
# Python - Direct Query
from django.contrib.gis.geos import Point
from geo.models import State

point = Point(72.8777, 19.0760, srid=4326)
state = State.objects.filter(geometry__contains=point).first()
print(f"Point is in: {state.name}")
```

```python
# Python - Using Utility Function
from geo.utils import point_in_state

state = point_in_state(lat=19.0760, lng=72.8777)
print(f"State: {state.name if state else 'Not found'}")
```

**Output:** `Maharashtra`

---

### 3. Find Which District Contains a Point

```sql
-- SQL
SELECT 
    d.name as district,
    s.name as state
FROM geo_district d
JOIN geo_state s ON d.state_id = s.id
WHERE ST_Contains(d.geometry, ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326));
```

```python
# Python
from geo.utils import point_in_district

district = point_in_district(lat=19.0760, lng=72.8777)
if district:
    print(f"{district.name}, {district.state.name}")
```

**Output:** `Mumbai, Maharashtra`

---

### 4. Get Centroid of a Polygon

```sql
-- SQL
SELECT 
    name,
    ST_AsText(ST_Centroid(geometry)) as centroid
FROM geo_state
WHERE name = 'Maharashtra';
```

```python
# Python
state = State.objects.get(name='Maharashtra')
centroid = state.geometry.centroid
print(f"Centroid: ({centroid.y}, {centroid.x})")  # (lat, lng)
```

**Output:** `Centroid: (19.6519, 75.9064)`

---

## 🔺 Polygon Operations

### 1. Calculate Area

```sql
-- SQL (Area in square meters, convert to km²)
SELECT 
    name,
    ST_Area(geography(geometry)) / 1000000 as area_km2
FROM geo_state
WHERE name = 'Maharashtra';
```

```python
# Python
from django.contrib.gis.measure import Area

state = State.objects.get(name='Maharashtra')
# Note: geometry.area gives degrees², need to use geography
area_km2 = state.geometry.area  # Approximation
# For accurate area, use geography cast in SQL
```

**Output:** `307713.0 km²`

---

### 2. Get Bounding Box

```sql
-- SQL
SELECT 
    name,
    ST_Extent(geometry) as bbox
FROM geo_state
WHERE name = 'Maharashtra'
GROUP BY name;
```

```python
# Python
state = State.objects.get(name='Maharashtra')
bbox = state.geometry.extent
# Returns: (min_lng, min_lat, max_lng, max_lat)
print(f"Bounding Box: {bbox}")
```

**Output:** `(72.6369, 15.6024, 80.8846, 22.0277)`

---

### 3. Simplify Geometry (Reduce Complexity)

```sql
-- SQL (Simplify to 0.01 degree tolerance)
SELECT 
    name,
    ST_AsGeoJSON(ST_Simplify(geometry, 0.01)) as simple_geojson
FROM geo_state
WHERE name = 'Maharashtra';
```

```python
# Python
state = State.objects.get(name='Maharashtra')
simplified = state.geometry.simplify(tolerance=0.01, preserve_topology=True)
print(f"Original points: {state.geometry.num_coords}")
print(f"Simplified points: {simplified.num_coords}")
```

---

## 📏 Distance & Proximity

### 1. Distance Between Two Points

```sql
-- SQL (Distance in meters)
SELECT 
    ST_Distance(
        geography(ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)),  -- Mumbai
        geography(ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326))   -- Pune
    ) / 1000 as distance_km;
```

```python
# Python
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance

mumbai = Point(72.8777, 19.0760, srid=4326)
pune = Point(73.8567, 18.5204, srid=4326)

# Convert to geography for accurate distance
distance_km = mumbai.distance(pune) * 111  # Approximate km conversion
# For accurate distance, use geography cast in SQL
```

**Output:** `118.5 km`

---

### 2. Find Districts Within Radius

```sql
-- SQL (Find districts within 50km of Mumbai)
SELECT 
    d.name,
    s.name as state,
    ST_Distance(
        geography(d.centroid),
        geography(ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326))
    ) / 1000 as distance_km
FROM geo_district d
JOIN geo_state s ON d.state_id = s.id
WHERE ST_DWithin(
    geography(d.centroid),
    geography(ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)),
    50000  -- 50km in meters
)
ORDER BY distance_km;
```

```python
# Python - Using Django GIS
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D  # D for Distance
from geo.models import District

center = Point(72.8777, 19.0760, srid=4326)
radius_km = 50

# Note: For accurate distance, use custom SQL or geography
districts = District.objects.filter(
    centroid__distance_lte=(center, D(km=radius_km))
).distance(center).order_by('distance')

for d in districts[:5]:
    print(f"{d.name}: {d.distance.km:.2f} km")
```

```python
# Python - Using Utility Function
from geo.utils import districts_within_radius

districts = districts_within_radius(
    lat=19.0760, 
    lng=72.8777, 
    radius_km=50
)

for district in districts:
    print(f"{district['name']}: {district['distance_km']:.2f} km")
```

**Output:**
```
Mumbai: 0.00 km
Thane: 25.30 km
Raigad: 45.80 km
```

---

### 3. Find Nearest District

```sql
-- SQL
SELECT 
    d.name,
    ST_Distance(
        geography(d.centroid),
        geography(ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326))
    ) / 1000 as distance_km
FROM geo_district d
ORDER BY d.centroid <-> ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)
LIMIT 1;
```

```python
# Python
from django.contrib.gis.geos import Point
from geo.models import District

point = Point(72.8777, 19.0760, srid=4326)
nearest = District.objects.annotate(
    distance=Distance('centroid', point)
).order_by('distance').first()

print(f"Nearest: {nearest.name}")
```

---

## 🔗 Spatial Relationships

### 1. Check if Point is Within Polygon

```sql
-- SQL
SELECT ST_Contains(
    (SELECT geometry FROM geo_state WHERE name = 'Maharashtra'),
    ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)
) as is_inside;
```

```python
# Python
from django.contrib.gis.geos import Point

state = State.objects.get(name='Maharashtra')
point = Point(72.8777, 19.0760, srid=4326)

is_inside = state.geometry.contains(point)
print(f"Point is inside: {is_inside}")
```

**Output:** `True`

---

### 2. Check if Polygons Intersect

```sql
-- SQL (Do Maharashtra and Karnataka share a border?)
SELECT ST_Intersects(
    (SELECT geometry FROM geo_state WHERE name = 'Maharashtra'),
    (SELECT geometry FROM geo_state WHERE name = 'Karnataka')
) as shares_border;
```

```python
# Python
maharashtra = State.objects.get(name='Maharashtra')
karnataka = State.objects.get(name='Karnataka')

shares_border = maharashtra.geometry.intersects(karnataka.geometry)
print(f"Shares border: {shares_border}")
```

**Output:** `True`

---

### 3. Check if Polygons Touch (Share Boundary)

```sql
-- SQL
SELECT ST_Touches(
    (SELECT geometry FROM geo_state WHERE name = 'Maharashtra'),
    (SELECT geometry FROM geo_state WHERE name = 'Gujarat')
) as touches;
```

```python
# Python
maharashtra = State.objects.get(name='Maharashtra')
gujarat = State.objects.get(name='Gujarat')

touches = maharashtra.geometry.touches(gujarat.geometry)
print(f"Touches: {touches}")
```

---

### 4. Find States Within Bounding Box

```sql
-- SQL
SELECT name
FROM geo_state
WHERE geometry && ST_MakeEnvelope(
    72.0, 18.0,  -- min_lng, min_lat
    74.0, 20.0,  -- max_lng, max_lat
    4326
);
```

```python
# Python
from geo.utils import states_in_bbox

states = states_in_bbox(
    min_lat=18.0, max_lat=20.0,
    min_lng=72.0, max_lng=74.0
)

for state in states:
    print(state.name)
```

---

## 🚀 Advanced Queries

### 1. Buffer Analysis (Create Circle Around Point)

```sql
-- SQL (20km buffer around Mumbai)
SELECT 
    d.name,
    s.name as state
FROM geo_district d
JOIN geo_state s ON d.state_id = s.id
WHERE ST_Intersects(
    d.geometry,
    ST_Buffer(
        geography(ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)),
        20000  -- 20km in meters
    )::geometry
);
```

```python
# Python
from django.contrib.gis.geos import Point
from geo.models import District

point = Point(72.8777, 19.0760, srid=4326)
buffer_distance = 20000  # meters

# Create buffer
buffer_geom = point.buffer(buffer_distance / 111000)  # Approximate degree conversion

districts = District.objects.filter(geometry__intersects=buffer_geom)
for d in districts:
    print(d.name)
```

---

### 2. Corridor Analysis (Buffer Along Line)

```sql
-- SQL (20km corridor from Mumbai to Pune)
WITH corridor AS (
    SELECT ST_Buffer(
        ST_MakeLine(
            ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)::geography,  -- Mumbai
            ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326)::geography   -- Pune
        ),
        20000  -- 20km buffer in meters
    )::geometry as buffer_geom
)
SELECT 
    d.name,
    s.name as state,
    d.population
FROM geo_district d
JOIN geo_state s ON d.state_id = s.id
CROSS JOIN corridor
WHERE ST_Intersects(d.geometry, corridor.buffer_geom);
```

```python
# Python - Using Utility Function
from geo.utils import analyze_market_corridor

result = analyze_market_corridor(
    start_lat=19.0760, start_lng=72.8777,  # Mumbai
    end_lat=18.5204, end_lng=73.8567,      # Pune
    buffer_km=20
)

print(f"Districts along route: {len(result['districts'])}")
print(f"Total population: {result['total_population']:,}")
for district in result['districts']:
    print(f"- {district['name']}: {district['population']:,}")
```

**Output:**
```
Districts along route: 3
Total population: 24,503,532
- Mumbai: 12,442,373
- Raigad: 2,634,200
- Pune: 9,426,959
```

---

### 3. Union (Combine Multiple Polygons)

```sql
-- SQL (Combine all Maharashtra districts into one polygon)
SELECT 
    ST_AsGeoJSON(ST_Union(geometry)) as combined_geometry
FROM geo_district
WHERE state_id = (SELECT id FROM geo_state WHERE name = 'Maharashtra');
```

```python
# Python
from django.contrib.gis.geos import MultiPolygon
from geo.models import District, State

maharashtra = State.objects.get(name='Maharashtra')
districts = maharashtra.districts.all()

# Union all district geometries
combined = districts.aggregate(
    union=Union('geometry')
)['union']

print(f"Combined geometry type: {combined.geom_type}")
```

---

### 4. Intersection (Find Overlapping Area)

```sql
-- SQL (Find intersection of two states - should be minimal/none)
SELECT 
    ST_AsGeoJSON(ST_Intersection(
        (SELECT geometry FROM geo_state WHERE name = 'Maharashtra'),
        (SELECT geometry FROM geo_state WHERE name = 'Gujarat')
    )) as intersection;
```

```python
# Python
mh = State.objects.get(name='Maharashtra')
gj = State.objects.get(name='Gujarat')

intersection = mh.geometry.intersection(gj.geometry)
if not intersection.empty:
    print(f"Intersection area: {intersection.area}")
```

---

### 5. Get All Neighboring States

```sql
-- SQL (States touching Maharashtra)
SELECT DISTINCT s2.name
FROM geo_state s1
JOIN geo_state s2 ON ST_Touches(s1.geometry, s2.geometry)
WHERE s1.name = 'Maharashtra';
```

```python
# Python
from geo.models import State

maharashtra = State.objects.get(name='Maharashtra')
neighbors = State.objects.filter(
    geometry__touches=maharashtra.geometry
)

for neighbor in neighbors:
    print(neighbor.name)
```

**Output:**
```
Gujarat
Madhya Pradesh
Chhattisgarh
Telangana
Karnataka
Goa
```

---

## ⚡ Performance Optimization

### 1. Create Spatial Index

```sql
-- SQL (Automatically created by Django, but manual example:)
CREATE INDEX idx_state_geometry ON geo_state USING GIST (geometry);
CREATE INDEX idx_district_geometry ON geo_district USING GIST (geometry);
CREATE INDEX idx_district_centroid ON geo_district USING GIST (centroid);
```

```python
# Python - In models.py (already done)
class State(gis_models.Model):
    geometry = gis_models.MultiPolygonField(srid=4326)  # Auto-indexed
```

**Check Indexes:**
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('geo_state', 'geo_district');
```

---

### 2. Use Bounding Box Filter First

```sql
-- SLOW (Full geometry comparison)
SELECT * FROM geo_district
WHERE ST_Contains(geometry, ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326));

-- FAST (Bounding box filter first, then precise check)
SELECT * FROM geo_district
WHERE geometry && ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)
  AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326));
```

---

### 3. Simplify Geometries for Display

```python
# For web maps, simplify geometries
from geo.models import State

states = State.objects.all()
geojson_features = []

for state in states:
    simplified = state.geometry.simplify(tolerance=0.01)
    geojson_features.append({
        'type': 'Feature',
        'geometry': json.loads(simplified.geojson),
        'properties': {'name': state.name}
    })
```

---

### 4. Use Geography for Distance Calculations

```sql
-- ACCURATE (Uses geography)
SELECT ST_Distance(
    geography(centroid),
    geography(ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326))
) / 1000 as distance_km
FROM geo_district;

-- APPROXIMATE (Uses geometry - faster but less accurate)
SELECT ST_Distance(
    centroid,
    ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326)
) * 111 as distance_km  -- 1 degree ≈ 111km
FROM geo_district;
```

---

## 🌍 Real-World Examples

### Example 1: Find Markets Near User Location

```python
def find_nearby_markets(user_lat, user_lng, radius_km=50):
    """Find all market zones within radius of user"""
    from django.contrib.gis.geos import Point
    from django.contrib.gis.measure import D
    from geo.models import MarketPotentialZone
    
    user_point = Point(user_lng, user_lat, srid=4326)
    
    nearby_zones = MarketPotentialZone.objects.filter(
        district__centroid__distance_lte=(user_point, D(km=radius_km)),
        potential_level='HIGH'
    ).select_related('district', 'state')
    
    return nearby_zones
```

---

### Example 2: Calculate Total Population Along Route

```python
def population_along_route(start_lat, start_lng, end_lat, end_lng, buffer_km=20):
    """Calculate total population within buffer of route"""
    from geo.utils import analyze_market_corridor
    
    result = analyze_market_corridor(
        start_lat=start_lat,
        start_lng=start_lng,
        end_lat=end_lat,
        end_lng=end_lng,
        buffer_km=buffer_km
    )
    
    return {
        'total_population': result['total_population'],
        'districts': len(result['districts']),
        'distance_km': result['distance_km']
    }

# Usage
stats = population_along_route(
    19.0760, 72.8777,  # Mumbai
    18.5204, 73.8567,  # Pune
    buffer_km=20
)
print(f"Population along route: {stats['total_population']:,}")
```

---

### Example 3: Find Best Market Zone

```python
def find_best_market_zone(product_type, min_population=1000000):
    """Find district with highest market potential"""
    from geo.models import MarketPotentialZone, District
    from django.db.models import Q
    
    zones = MarketPotentialZone.objects.filter(
        product_type=product_type,
        potential_level='HIGH',
        district__population__gte=min_population
    ).select_related('district', 'state').order_by('-market_score')
    
    if zones.exists():
        best = zones.first()
        return {
            'district': best.district.name,
            'state': best.state.name,
            'score': best.market_score,
            'population': best.estimated_target_population
        }
    return None

# Usage
best_zone = find_best_market_zone('Premium Smartphone')
if best_zone:
    print(f"Best market: {best_zone['district']}, {best_zone['state']}")
    print(f"Score: {best_zone['score']}")
```

---

## 📚 Useful Resources

### PostGIS Functions Reference

| Function | Purpose | Example |
|----------|---------|---------|
| `ST_Contains` | Point in polygon | `ST_Contains(poly, point)` |
| `ST_Within` | Opposite of contains | `ST_Within(point, poly)` |
| `ST_Intersects` | Geometries overlap | `ST_Intersects(poly1, poly2)` |
| `ST_Distance` | Distance between | `ST_Distance(geog1, geog2)` |
| `ST_DWithin` | Within distance | `ST_DWithin(geog1, geog2, dist)` |
| `ST_Buffer` | Create buffer | `ST_Buffer(geog, radius)` |
| `ST_Centroid` | Get center point | `ST_Centroid(poly)` |
| `ST_Area` | Calculate area | `ST_Area(geography(poly))` |
| `ST_Union` | Combine geometries | `ST_Union(poly1, poly2)` |
| `ST_Intersection` | Find overlap | `ST_Intersection(poly1, poly2)` |

### Django GIS Lookups

| Lookup | SQL Equivalent | Example |
|--------|----------------|---------|
| `contains` | `ST_Contains` | `geometry__contains=point` |
| `intersects` | `ST_Intersects` | `geometry__intersects=poly` |
| `within` | `ST_Within` | `point__within=poly` |
| `distance_lte` | `ST_DWithin` | `point__distance_lte=(pt, D(km=50))` |
| `touches` | `ST_Touches` | `geometry__touches=other` |
| `overlaps` | `ST_Overlaps` | `geometry__overlaps=other` |

---

**Last Updated:** October 17, 2025  
**PostGIS Version:** 3.3+  
**Django GIS:** 5.2+
