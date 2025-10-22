from django.db import connection
import json


def _fetch_single_json(query: str, params=None):
    """Execute a query that returns a single column containing JSON/JSONB.
    Returns a Python dict/list parsed from JSON, or None.
    """
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        row = cursor.fetchone()
        if not row:
            return None
        data = row[0]
        # If DB returns a string, parse it
        if isinstance(data, str):
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                # Some drivers may already adapt jsonb to dict
                return data
        return data


# ==================== A) Frontend GeoJSON endpoints ====================

def states_geojson():
    query = """
    SELECT jsonb_build_object(
      'type', 'FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(s.geometry)::jsonb,
          'properties', jsonb_build_object(
            'id', s.id,
            'name', s.name,
            'code', s.code,
            'population', s.population,
            'density', s.population_density,
            'centroid_lat', ST_Y(ST_Centroid(s.geometry)),
            'centroid_lng', ST_X(ST_Centroid(s.geometry))
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_state AS s;
    """
    return _fetch_single_json(query)


def districts_geojson(state_name=None):
    # Use conditional WHERE with NULL parameter
    query = """
    SELECT jsonb_build_object(
      'type', 'FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(d.geometry)::jsonb,
          'properties', jsonb_build_object(
            'id', d.id,
            'name', d.name,
            'state', s.name,
            'population', d.population,
            'literacy_rate', d.literacy_rate,
            'centroid_lat', CASE WHEN d.centroid IS NOT NULL THEN ST_Y(d.centroid) ELSE NULL END,
            'centroid_lng', CASE WHEN d.centroid IS NOT NULL THEN ST_X(d.centroid) ELSE NULL END
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district AS d
    JOIN geo_state AS s ON s.id = d.state_id
    WHERE (%s IS NULL OR s.name = %s);
    """
    return _fetch_single_json(query, [state_name, state_name])


def market_zones_geojson(product_type=None):
    query = """
    SELECT jsonb_build_object(
      'type', 'FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type', 'Feature',
          'geometry', ST_AsGeoJSON(d.centroid)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name || ', ' || s.name,
            'state', s.name,
            'product_type', z.product_type,
            'potential_level', z.potential_level,
            'market_score', z.market_score,
            'predicted_reach', z.predicted_reach_percentage
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_marketpotentialzone AS z
    JOIN geo_state AS s ON s.id = z.state_id
    LEFT JOIN geo_district AS d ON d.id = z.district_id
    WHERE (%s IS NULL OR z.product_type = %s);
    """
    return _fetch_single_json(query, [product_type, product_type])


# ==================== 1) - 9) Spatial queries ====================

def districts_within_radius(lat, lng, radius_km):
    query = """
    WITH params AS (
      SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS pt,
             (%s)::float AS radius_km
    )
    SELECT d.id, d.name, d.population, d.state_id,
           ST_DistanceSphere(d.centroid, p.pt) AS distance_m,
           ST_DistanceSphere(d.centroid, p.pt) / 1000.0 AS distance_km,
           ST_X(d.centroid) AS lng, ST_Y(d.centroid) AS lat
    FROM geo_district AS d
    CROSS JOIN params AS p
    WHERE ST_DistanceSphere(d.centroid, p.pt) <= p.radius_km * 1000.0
    ORDER BY distance_m ASC;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [lng, lat, radius_km])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def state_containing_point(lat, lng):
    query = """
    SELECT s.id, s.name, s.code, s.population
    FROM geo_state AS s
    WHERE ST_Contains(
            s.geometry,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
          )
    LIMIT 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [lng, lat])
        row = cursor.fetchone()
        if not row:
            return None
        cols = [c[0] for c in cursor.description]
        return dict(zip(cols, row))


def district_containing_point(lat, lng):
    query = """
    SELECT d.id, d.name, d.population, d.literacy_rate
    FROM geo_district AS d
    WHERE ST_Contains(
            d.geometry,
            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
          )
    LIMIT 1;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [lng, lat])
        row = cursor.fetchone()
        if not row:
            return None
        cols = [c[0] for c in cursor.description]
        return dict(zip(cols, row))


def neighboring_districts(district_id):
    query = """
    WITH target AS (
      SELECT geometry FROM geo_district WHERE id = %s
    )
    SELECT d.id, d.name, d.population, d.state_id
    FROM geo_district AS d, target AS t
    WHERE d.id <> %s
      AND ST_Touches(d.geometry, t.geometry);
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [district_id, district_id])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def states_intersecting_area(polygon_geojson: dict):
    query = """
    SELECT s.id, s.name, ST_Area(s.geometry) AS intersection_area
    FROM geo_state AS s
    WHERE ST_Intersects(
            s.geometry,
            ST_GeomFromGeoJSON(%s)
          )
    ORDER BY intersection_area DESC;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [json.dumps(polygon_geojson)])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def distance_between_districts(d1_id, d2_id):
    query = """
    SELECT ST_DistanceSphere(d1.centroid, d2.centroid) AS distance_m,
           ST_DistanceSphere(d1.centroid, d2.centroid) / 1000.0 AS distance_km
    FROM geo_district AS d1
    CROSS JOIN geo_district AS d2
    WHERE d1.id = %s AND d2.id = %s;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [d1_id, d2_id])
        row = cursor.fetchone()
        if not row:
            return None
        return {'distance_m': float(row[0]), 'distance_km': float(row[1])}


def analyze_market_corridor(start_lat, start_lng, end_lat, end_lng, buffer_km):
    query = """
    WITH line AS (
      SELECT ST_SetSRID(
               ST_MakeLine(
                 ST_MakePoint(%s, %s),
                 ST_MakePoint(%s, %s)
               ), 4326
             ) AS geom
    ), buf AS (
      SELECT ST_Buffer(geom, (%s / 111.0)) AS geom
      FROM line
    )
    SELECT d.id, d.name, d.population, d.state_id
    FROM geo_district AS d
    CROSS JOIN buf
    WHERE ST_Intersects(d.geometry, buf.geom);
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [start_lng, start_lat, end_lng, end_lat, buffer_km])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def market_reach_radius(base_district_id, radius_km):
    query = """
    WITH base AS (
      SELECT centroid AS base_pt
      FROM geo_district WHERE id = %s
    )
    SELECT d.id, d.name, d.population, d.state_id
    FROM geo_district AS d, base
    WHERE ST_DWithin(
            d.geometry::geography,
            base.base_pt::geography,
            %s * 1000.0
          );
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [base_district_id, radius_km])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def competitive_density_map(product_type, lat, lng, radius_km):
    query = """
    WITH params AS (
      SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS pt,
             (%s)::float AS radius_km
    )
    SELECT z.id, z.product_type, z.potential_level, z.market_score,
           z.predicted_reach_percentage,
           d.id AS district_id,
           ST_DistanceSphere(d.centroid, p.pt) AS distance_m,
           ST_DistanceSphere(d.centroid, p.pt) / 1000.0 AS distance_km
    FROM geo_marketpotentialzone AS z
    JOIN geo_district AS d ON d.id = z.district_id
    CROSS JOIN params AS p
    WHERE z.product_type = %s
      AND ST_DWithin(d.geometry::geography, p.pt::geography, p.radius_km * 1000.0)
    ORDER BY distance_m ASC;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [lng, lat, radius_km, product_type])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ==================== B) Dashboard analytics (GeoJSON) ====================

def b1_population_density_geojson(state_name=None):
    query = """
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(d.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name,
            'state', s.name,
            'population', d.population,
            'area_km2', d.area_km2,
            'population_density', CASE WHEN d.area_km2 IS NOT NULL AND d.area_km2 > 0 THEN (d.population::numeric / NULLIF(d.area_km2,0)) ELSE NULL END
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    WHERE (%s IS NULL OR s.name = %s);
    """
    return _fetch_single_json(query, [state_name, state_name])


def b2_spending_choropleth_geojson(state_name=None):
    query = """
    WITH spend AS (
      SELECT dp.district_id, AVG(dp.avg_spending)::numeric AS avg_spending
      FROM geo_demographicprofile dp
      WHERE dp.avg_spending IS NOT NULL
      GROUP BY dp.district_id
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(d.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name,
            'state', s.name,
            'avg_spending', sp.avg_spending
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    LEFT JOIN spend sp ON sp.district_id = d.id
    WHERE (%s IS NULL OR s.name = %s);
    """
    return _fetch_single_json(query, [state_name, state_name])


def b3_unemployment_bubbles_geojson(state_name=None):
    query = """
    WITH latest_ei AS (
      SELECT DISTINCT ON (ei.district_id)
             ei.district_id,
             ei.unemployment_rate,
             ei.employment_rate,
             ei.date_recorded
      FROM geo_economicindicator ei
      WHERE ei.district_id IS NOT NULL
      ORDER BY ei.district_id, ei.date_recorded DESC NULLS LAST
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(d.centroid)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name,
            'state', s.name,
            'unemployment_rate', le.unemployment_rate,
            'employment_rate', le.employment_rate,
            'date_recorded', le.date_recorded
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    LEFT JOIN latest_ei le ON le.district_id = d.id
    WHERE d.centroid IS NOT NULL
      AND (%s IS NULL OR s.name = %s);
    """
    return _fetch_single_json(query, [state_name, state_name])


def b4_top_spending_cities(limit=10):
    query = """
    WITH spend AS (
      SELECT dp.district_id, AVG(dp.avg_spending)::numeric AS avg_spending
      FROM geo_demographicprofile dp
      WHERE dp.avg_spending IS NOT NULL
      GROUP BY dp.district_id
    )
    SELECT d.id, d.name AS district, s.name AS state, sp.avg_spending,
           ST_AsGeoJSON(d.centroid)::jsonb AS geometry
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    JOIN spend sp ON sp.district_id = d.id
    ORDER BY sp.avg_spending DESC NULLS LAST
    LIMIT %s;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [limit])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b5_savings_leaderboard(limit=10):
    query = """
    WITH agg AS (
      SELECT dp.district_id,
             AVG(dp.avg_disposable_income)::numeric AS avg_disposable_income,
             AVG(dp.avg_spending)::numeric AS avg_spending
      FROM geo_demographicprofile dp
      GROUP BY dp.district_id
    )
    SELECT d.id, d.name AS district, s.name AS state,
           (agg.avg_disposable_income - agg.avg_spending) AS savings_est,
           agg.avg_disposable_income, agg.avg_spending,
           ST_AsGeoJSON(d.centroid)::jsonb AS geometry
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    JOIN agg ON agg.district_id = d.id
    ORDER BY savings_est DESC NULLS LAST
    LIMIT %s;
    """
    with connection.cursor() as cursor:
        cursor.execute(query, [limit])
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b6_whitespaces_geojson(product_type=None):
    query = """
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(d.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name,
            'state', s.name,
            'uncovered', TRUE
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    WHERE NOT EXISTS (
      SELECT 1 FROM geo_marketpotentialzone z
      WHERE z.district_id = d.id
        AND (%s IS NULL OR z.product_type = %s)
    );
    """
    return _fetch_single_json(query, [product_type, product_type])


def b7_literacy_income_scatter():
    query = """
    WITH inc AS (
      SELECT dp.district_id, AVG(dp.avg_income)::numeric AS avg_income
      FROM geo_demographicprofile dp
      WHERE dp.avg_income IS NOT NULL
      GROUP BY dp.district_id
    )
    SELECT d.id, d.name AS district, s.name AS state,
           d.literacy_rate::numeric AS literacy_rate,
           inc.avg_income,
           ST_X(d.centroid) AS lng, ST_Y(d.centroid) AS lat
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    LEFT JOIN inc ON inc.district_id = d.id
    WHERE d.centroid IS NOT NULL
      AND (d.literacy_rate IS NOT NULL OR inc.avg_income IS NOT NULL);
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b8_market_accessibility_geojson(w_popdens=1.0, w_income=1.0, w_emprate=1.0):
    query = """
    WITH base AS (
      SELECT d.id, d.name, s.name AS state, d.geometry,
             (CASE WHEN d.area_km2 IS NOT NULL AND d.area_km2 > 0 THEN d.population::numeric / d.area_km2 ELSE NULL END) AS pop_density,
             (SELECT AVG(dp.avg_disposable_income) FROM geo_demographicprofile dp WHERE dp.district_id = d.id) AS avg_income,
             (SELECT ei.employment_rate FROM geo_economicindicator ei WHERE ei.district_id = d.id ORDER BY ei.date_recorded DESC NULLS LAST LIMIT 1) AS employment_rate
      FROM geo_district d JOIN geo_state s ON s.id = d.state_id
    ), mm AS (
      SELECT MIN(pop_density) min_pd, MAX(pop_density) max_pd,
             MIN(avg_income)  min_ai, MAX(avg_income)  max_ai,
             MIN(employment_rate) min_er, MAX(employment_rate) max_er
      FROM base
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(b.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', b.name,
            'state', b.state,
            'market_accessibility_score',
              %s * CASE WHEN mm.max_pd>mm.min_pd AND b.pop_density IS NOT NULL THEN (b.pop_density - mm.min_pd)/(mm.max_pd - mm.min_pd) ELSE 0 END +
              %s * CASE WHEN mm.max_ai>mm.min_ai AND b.avg_income  IS NOT NULL THEN (b.avg_income  - mm.min_ai)/(mm.max_ai - mm.min_ai) ELSE 0 END +
              %s * CASE WHEN mm.max_er>mm.min_er AND b.employment_rate IS NOT NULL THEN (b.employment_rate - mm.min_er)/(mm.max_er - mm.min_er) ELSE 0 END
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM base b CROSS JOIN mm;
    """
    return _fetch_single_json(query, [w_popdens, w_income, w_emprate])


def b9_avg_disposable_income_geojson():
    query = """
    WITH agg AS (
      SELECT dp.district_id, AVG(dp.avg_disposable_income)::numeric AS avg_disposable_income
      FROM geo_demographicprofile dp
      WHERE dp.avg_disposable_income IS NOT NULL
      GROUP BY dp.district_id
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(d.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name,
            'state', s.name,
            'avg_disposable_income', agg.avg_disposable_income
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    LEFT JOIN agg ON agg.district_id = d.id;
    """
    return _fetch_single_json(query)


def b10_affordability_index_geojson():
    query = """
    WITH base AS (
      SELECT d.id, d.geometry, s.name AS state, d.name,
             (SELECT AVG(dp.avg_disposable_income) FROM geo_demographicprofile dp WHERE dp.district_id = d.id) AS adi
      FROM geo_district d JOIN geo_state s ON s.id = d.state_id
    ), mm AS (
      SELECT MIN(adi) min_adi, MAX(adi) max_adi FROM base
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(b.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', b.name,
            'state', b.state,
            'affordability_index', CASE WHEN mm.max_adi>mm.min_adi AND b.adi IS NOT NULL THEN (b.adi - mm.min_adi)/(mm.max_adi - mm.min_adi) ELSE NULL END
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM base b CROSS JOIN mm;
    """
    return _fetch_single_json(query)


def b11_spending_elasticity():
    query = """
    WITH agg AS (
      SELECT dp.district_id,
             AVG(dp.avg_spending)::numeric AS avg_spending,
             AVG(dp.avg_disposable_income)::numeric AS avg_disposable_income
      FROM geo_demographicprofile dp
      GROUP BY dp.district_id
    )
    SELECT d.id, d.name AS district, s.name AS state,
           CASE WHEN agg.avg_disposable_income IS NOT NULL AND agg.avg_disposable_income <> 0
                THEN (agg.avg_spending / agg.avg_disposable_income) END AS elasticity_ratio,
           agg.avg_spending, agg.avg_disposable_income,
           ST_AsGeoJSON(d.centroid)::jsonb AS geometry
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    JOIN agg ON agg.district_id = d.id;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b12_purchase_frequency_geojson():
    query = """
    WITH agg AS (
      SELECT dp.district_id, AVG(dp.avg_purchase_frequency)::numeric AS avg_purchase_frequency
      FROM geo_demographicprofile dp
      WHERE dp.avg_purchase_frequency IS NOT NULL
      GROUP BY dp.district_id
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(d.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', d.name,
            'state', s.name,
            'avg_purchase_frequency', agg.avg_purchase_frequency
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    LEFT JOIN agg ON agg.district_id = d.id;
    """
    return _fetch_single_json(query)


def b13_profitability_proxy_by_state():
    query = """
    WITH spend AS (
      SELECT dp.state_id, AVG(dp.avg_spending)::numeric AS avg_spending
      FROM geo_demographicprofile dp
      WHERE dp.avg_spending IS NOT NULL
      GROUP BY dp.state_id
    ),
    latest_salary AS (
      SELECT DISTINCT ON (ei.state_id)
             ei.state_id,
             ei.avg_monthly_salary,
             ei.date_recorded
      FROM geo_economicindicator ei
      WHERE ei.avg_monthly_salary IS NOT NULL
      ORDER BY ei.state_id, ei.date_recorded DESC NULLS LAST
    )
    SELECT s.id AS state_id, s.name AS state,
           sp.avg_spending,
           ls.avg_monthly_salary,
           CASE WHEN ls.avg_monthly_salary IS NOT NULL AND ls.avg_monthly_salary <> 0
                THEN (sp.avg_spending / ls.avg_monthly_salary) END AS profitability_proxy,
           ST_AsGeoJSON(s.geometry)::jsonb AS geometry
    FROM geo_state s
    LEFT JOIN spend sp ON sp.state_id = s.id
    LEFT JOIN latest_salary ls ON ls.state_id = s.id;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b14_hri_geojson(w_spend=1.0, w_emp=1.0):
    query = """
    WITH base AS (
      SELECT d.id, d.geometry, d.name, s.name AS state,
             (SELECT AVG(dp.avg_spending) FROM geo_demographicprofile dp WHERE dp.district_id = d.id) AS avg_spending,
             (SELECT ei.employment_rate FROM geo_economicindicator ei WHERE ei.district_id = d.id ORDER BY ei.date_recorded DESC NULLS LAST LIMIT 1) AS employment_rate
      FROM geo_district d JOIN geo_state s ON s.id = d.state_id
    ), mm AS (
      SELECT MIN(avg_spending) min_sp, MAX(avg_spending) max_sp,
             MIN(employment_rate) min_er, MAX(employment_rate) max_er
      FROM base
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(b.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', b.name,
            'state', b.state,
            'hri', %s * CASE WHEN mm.max_sp>mm.min_sp AND b.avg_spending IS NOT NULL THEN (b.avg_spending - mm.min_sp)/(mm.max_sp - mm.min_sp) ELSE 0 END +
                   %s * CASE WHEN mm.max_er>mm.min_er AND b.employment_rate IS NOT NULL THEN (b.employment_rate - mm.min_er)/(mm.max_er - mm.min_er) ELSE 0 END
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM base b CROSS JOIN mm;
    """
    return _fetch_single_json(query, [w_spend, w_emp])


def b15_district_penetration_rate():
    query = """
    WITH samp AS (
      SELECT dp.district_id, SUM(dp.sample_size) AS sample_size
      FROM geo_demographicprofile dp
      GROUP BY dp.district_id
    )
    SELECT d.id, d.name AS district, s.name AS state,
           CASE WHEN d.population IS NOT NULL AND d.population <> 0
                THEN (COALESCE(samp.sample_size,0)::numeric / d.population::numeric) END AS penetration_rate_proxy,
           COALESCE(samp.sample_size,0) AS sample_size,
           d.population
    FROM geo_district d
    JOIN geo_state s ON s.id = d.state_id
    LEFT JOIN samp ON samp.district_id = d.id
    ORDER BY penetration_rate_proxy DESC NULLS LAST;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b16_geo_concentration_index():
    query = """
    WITH spend AS (
      SELECT d.state_id, d.id AS district_id, AVG(dp.avg_spending)::numeric AS avg_spending
      FROM geo_district d
      JOIN geo_demographicprofile dp ON dp.district_id = d.id
      GROUP BY d.state_id, d.id
    ), totals AS (
      SELECT state_id, SUM(avg_spending) AS total_spending FROM spend GROUP BY state_id
    ), shares AS (
      SELECT s.state_id, s.district_id,
             CASE WHEN t.total_spending > 0 THEN (s.avg_spending / t.total_spending) ELSE NULL END AS share
      FROM spend s JOIN totals t ON t.state_id = s.state_id
    )
    SELECT st.id AS state_id, st.name AS state,
           SUM( (sh.share * sh.share) ) AS hhi,
           ST_AsGeoJSON(st.geometry)::jsonb AS geometry
    FROM geo_state st
    JOIN shares sh ON sh.state_id = st.id
    GROUP BY st.id, st.name, st.geometry
    ORDER BY hhi DESC NULLS LAST;
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = [c[0] for c in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]


def b17_expansion_opportunity_geojson(product_type=None, w_pd=1.0, w_income=1.0, w_lowpen=1.0):
    query = """
    WITH base AS (
      SELECT d.id, d.geometry, d.name, s.name AS state,
             (CASE WHEN d.area_km2 IS NOT NULL AND d.area_km2 > 0 THEN d.population::numeric / d.area_km2 ELSE NULL END) AS pop_density,
             (SELECT AVG(dp.avg_disposable_income) FROM geo_demographicprofile dp WHERE dp.district_id = d.id) AS avg_income
      FROM geo_district d JOIN geo_state s ON s.id = d.state_id
    ), zc AS (
      SELECT d.id AS district_id, COUNT(z.id) AS zones
      FROM geo_district d
      LEFT JOIN geo_marketpotentialzone z ON z.district_id = d.id AND (%s IS NULL OR z.product_type = %s)
      GROUP BY d.id
    ), mm AS (
      SELECT MIN(b.pop_density) min_pd, MAX(b.pop_density) max_pd,
             MIN(b.avg_income)  min_ai, MAX(b.avg_income)  max_ai,
             MIN(COALESCE(zc.zones,0)) min_z, MAX(COALESCE(zc.zones,0)) max_z
      FROM base b LEFT JOIN zc ON zc.district_id = b.id
    )
    SELECT jsonb_build_object(
      'type','FeatureCollection',
      'features', COALESCE(jsonb_agg(
        jsonb_build_object(
          'type','Feature',
          'geometry', ST_AsGeoJSON(b.geometry)::jsonb,
          'properties', jsonb_build_object(
            'name', b.name,
            'state', b.state,
            'expansion_opportunity_index',
               %s * CASE WHEN mm.max_pd>mm.min_pd AND b.pop_density IS NOT NULL THEN (b.pop_density - mm.min_pd)/(mm.max_pd - mm.min_pd) ELSE 0 END +
               %s * CASE WHEN mm.max_ai>mm.min_ai AND b.avg_income  IS NOT NULL THEN (b.avg_income  - mm.min_ai)/(mm.max_ai - mm.min_ai) ELSE 0 END +
               %s * (1 - CASE WHEN mm.max_z>mm.min_z THEN (COALESCE(zc.zones,0) - mm.min_z)::numeric / NULLIF(mm.max_z - mm.min_z,0) ELSE 0 END)
          )
        )
      ), '[]'::jsonb)
    ) AS geojson
    FROM base b LEFT JOIN zc ON zc.district_id = b.id CROSS JOIN mm;
    """
    return _fetch_single_json(query, [product_type, product_type, w_pd, w_income, w_lowpen])
