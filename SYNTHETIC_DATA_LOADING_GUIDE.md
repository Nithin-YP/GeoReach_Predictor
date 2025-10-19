# 📊 Synthetic Data Loading Guide

**Project:** GeoReach Predictor  
**Purpose:** Load and populate synthetic/sample data for development and testing  
**Last Updated:** October 17, 2025

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Data Sources](#data-sources)
4. [Loading Geographic Data](#loading-geographic-data)
5. [Loading Economic & Demographic Data](#loading-economic--demographic-data)
6. [Complete Setup Workflow](#complete-setup-workflow)
7. [Verification & Testing](#verification--testing)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This guide walks you through loading all synthetic/sample data into the GeoReach Predictor database. The data includes:

- **Geographic Boundaries:** Indian states and districts with real MultiPolygon geometries
- **Economic Indicators:** Employment, unemployment, income data
- **Demographic Profiles:** Age groups, education levels, spending patterns
- **Industry Data:** Employment by industry sector
- **Market Zones:** Calculated market potential areas

---

## ✅ Prerequisites

### 1. Database Setup

Ensure PostgreSQL with PostGIS is running:

```bash
# Check PostgreSQL status
# Windows:
pg_ctl status

# Linux/Mac:
sudo systemctl status postgresql
```

### 2. Database Created

```sql
-- In psql terminal
CREATE DATABASE georeach_db;
CREATE USER georeach WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE georeach_db TO georeach;

\c georeach_db
CREATE EXTENSION postgis;
```

### 3. Environment Configured

Create `.env` file:
```env
DATABASE_URL=postgis://georeach:your_password@localhost:5432/georeach_db
SECRET_KEY=your-secret-key-here
DEBUG=True
```

### 4. Migrations Applied

```bash
python manage.py migrate
```

---

## 📂 Data Sources

### Geographic Data (Shapefiles)

Located in: `datasets/geodata/`

| File | Description | Features | Size |
|------|-------------|----------|------|
| `india_states.shp` | State boundaries | 37 states | MultiPolygon |
| `india_districts.shp` | District boundaries | 670+ districts | MultiPolygon |

**Associated Files:**
- `.shx` - Shape index
- `.dbf` - Attribute data
- `.prj` - Projection info
- `.cpg` - Character encoding

**Data Source:** GADM (Global Administrative Areas)

---

### CSV Datasets

Located in: `datasets/`

| File | Rows | Description |
|------|------|-------------|
| `Customer_Spend.csv` | ~1000 | Customer spending patterns |
| `Employment_India.csv` | ~500 | Employment statistics |
| `Income_Expenditure.csv` | ~800 | Income and expenditure data |
| `India_Districts_Population.csv` | ~670 | District population data |
| `Indian_Personal_Finance.csv` | ~1200 | Personal finance records |
| `Population_of_India.csv` | ~37 | State population data |
| `Unemployment_India.csv` | ~400 | Unemployment rates |

---

## 🗺️ Loading Geographic Data

### Step 1: Inspect Shapefiles (Optional)

```bash
python inspect_shapefiles.py
```

**Expected Output:**
```
====================================
SHAPEFILE: datasets/geodata/india_states.shp
====================================

Field Structure:
- NAME: String (width: 50)
- NAME_1: String (width: 50)
- ENGTYPE_1: String (width: 25)

Geometry Type: MultiPolygon
Total Features: 37

Sample Features:
1. Maharashtra
2. Uttar Pradesh
3. Tamil Nadu
...
```

---

### Step 2: Load State and District Boundaries

```bash
python load_real_shapefiles.py
```

**What This Does:**

1. **Loads States:**
   - Reads `india_states.shp`
   - Extracts MultiPolygon geometries
   - Populates State model (37 states)
   - Calculates centroids automatically

2. **Loads Districts:**
   - Reads `india_districts.shp`
   - Links districts to states
   - Extracts population data
   - Populates District model (670+ districts)

**Expected Output:**
```
Loading States from shapefile...
Found 37 features in shapefile

Processing states:
✓ Maharashtra created
✓ Uttar Pradesh created
✓ Tamil Nadu created
...
Successfully loaded 37 states

Loading Districts from shapefile...
Found 676 features in shapefile

Processing districts:
✓ Mumbai, Maharashtra created
✓ Pune, Maharashtra created
✓ Thane, Maharashtra created
...
Successfully loaded 670 districts

Summary:
- States: 37
- Districts: 670
- Total geometries loaded
```

**Database Impact:**
```sql
-- Check loaded data
SELECT COUNT(*) FROM geo_state;    -- 37
SELECT COUNT(*) FROM geo_district; -- 670+
```

---

### Step 3: Verify Geographic Data

```bash
# Using Django shell
python manage.py shell

# In Python shell:
from geo.models import State, District

# Check counts
print(f"States: {State.objects.count()}")
print(f"Districts: {District.objects.count()}")

# Check a state
maharashtra = State.objects.get(name='Maharashtra')
print(f"State: {maharashtra.name}")
print(f"Centroid: {maharashtra.centroid}")
print(f"Districts: {maharashtra.districts.count()}")

# Check a district
mumbai = District.objects.get(name='Mumbai')
print(f"District: {mumbai.name}")
print(f"State: {mumbai.state.name}")
print(f"Population: {mumbai.population}")
```

---

## 📊 Loading Economic & Demographic Data

### Step 4: Populate Sample Data

```bash
python check_and_populate_data.py
```

**What This Does:**

#### a) **Economic Indicators (8 records)**
- Unemployment rates
- Employment rates
- Average monthly salary
- Labour participation rate
- Sample data for major states

```python
# Example data created:
EconomicIndicator(
    state=maharashtra,
    area_type='URBAN',
    unemployment_rate=4.5,
    employment_rate=95.5,
    avg_monthly_salary=45000.00,
    date_recorded='2024-01-01'
)
```

#### b) **Demographic Profiles (45 records)**
- Age groups: 18-24, 25-34, 35-44, 45-54, 55+
- City tiers: TIER_1, TIER_2, TIER_3
- Education levels
- Income and spending patterns
- Linked to districts

```python
# Example data created:
DemographicProfile(
    state=maharashtra,
    district=mumbai,
    age_group='25-34',
    education_level='BACHELOR',
    city_tier='TIER_1',
    avg_income=60000.00,
    avg_spending=45000.00,
    groceries_expenditure=8000.00
)
```

#### c) **Industry Employment (30 records)**
- Industries: Technology, Retail, Healthcare, etc.
- Employed/unemployed counts
- Average salaries
- Distribution across states

```python
# Example data created:
IndustryEmployment(
    state=maharashtra,
    district=pune,
    industry='TECHNOLOGY',
    employed_count=250000,
    avg_salary=80000.00
)
```

#### d) **Market Potential Zones (3 records)**
- High/Medium/Low potential areas
- Product-specific zones
- Market scores
- Target population estimates

```python
# Example data created:
MarketPotentialZone(
    state=maharashtra,
    district=mumbai,
    product_type='Premium Smartphone',
    potential_level='HIGH',
    market_score=85.5,
    estimated_target_population=2500000
)
```

**Expected Output:**
```
====================================
Data Population Summary
====================================

Checking existing data...
States: 37
Districts: 670

Populating Economic Indicators...
✓ Created 8 economic indicator records

Populating Demographic Profiles...
✓ Created 45 demographic profiles

Populating Industry Employment...
✓ Created 30 industry employment records

Populating Market Potential Zones...
✓ Created 3 market zones

====================================
FINAL DATABASE STATUS
====================================
States: 37
Districts: 670
Economic Indicators: 8
Demographic Profiles: 45
Industry Employment: 30
Market Potential Zones: 3

✓ All synthetic data loaded successfully!
```

---

## 🔄 Complete Setup Workflow

### Full Setup from Scratch

```bash
# 1. Create virtual environment
conda create -n georeach python=3.12
conda activate georeach

# 2. Install dependencies
conda install -c conda-forge gdal geos proj
pip install -r requirements.txt

# 3. Setup database
createdb georeach_db
psql -d georeach_db -c "CREATE EXTENSION postgis;"

# 4. Configure environment
cp .env.example .env
# Edit .env with your settings

# 5. Run migrations
python manage.py migrate

# 6. Load geographic boundaries
python load_real_shapefiles.py

# 7. Load economic/demographic data
python check_and_populate_data.py

# 8. Create admin user
python manage.py create_admin

# 9. Train ML models (optional)
python manage.py train_models

# 10. Start server
python manage.py runserver
```

**Total Time:** ~10 minutes (excluding downloads)

---

## ✅ Verification & Testing

### 1. Database Verification

```bash
python manage.py shell
```

```python
from geo.models import *

# Check all counts
print(f"States: {State.objects.count()}")
print(f"Districts: {District.objects.count()}")
print(f"Economic Indicators: {EconomicIndicator.objects.count()}")
print(f"Demographic Profiles: {DemographicProfile.objects.count()}")
print(f"Industry Employment: {IndustryEmployment.objects.count()}")
print(f"Market Zones: {MarketPotentialZone.objects.count()}")

# Verify spatial data
maharashtra = State.objects.first()
print(f"Geometry type: {maharashtra.geometry.geom_type}")
print(f"Has centroid: {maharashtra.centroid is not None}")
```

### 2. API Verification

```bash
# Start server
python manage.py runserver

# In another terminal, test APIs:
curl http://127.0.0.1:8000/geo/api/states/
curl http://127.0.0.1:8000/geo/api/districts/
curl http://127.0.0.1:8000/geo/api/economic-indicators/
curl http://127.0.0.1:8000/geo/api/demographics/
```

### 3. Comprehensive Health Check

```bash
python check_all_functionalities.py
```

**Expected Output:**
```
====================================
Database Health Check
====================================
✓ States: 37
✓ Districts: 670
✓ Economic Indicators: 8
✓ Demographic Profiles: 45
✓ Industry Employment: 30
✓ Market Potential Zones: 3

Database Health: 100%

====================================
Spatial Data Check
====================================
✓ All states have geometry
✓ All districts have geometry
✓ Centroids calculated

Spatial Data Health: 100%

====================================
API Endpoints Check
====================================
✓ /geo/api/states/ - 200 OK
✓ /geo/api/districts/ - 200 OK
✓ /geo/api/economic-indicators/ - 200 OK
✓ /geo/api/demographics/ - 200 OK

API Health: 100%

Overall System Health: 100% ✓
```

---

## 🔧 Troubleshooting

### Issue 1: Shapefile Not Found

**Error:**
```
FileNotFoundError: datasets/geodata/india_states.shp
```

**Solution:**
```bash
# Check if files exist
ls datasets/geodata/

# Download shapefiles if missing
# (Provide download link or instructions)
```

---

### Issue 2: GDAL Import Error

**Error:**
```
ImportError: No module named 'osgeo'
```

**Solution:**
```bash
# Install GDAL
conda install -c conda-forge gdal

# Or on Ubuntu:
sudo apt-get install gdal-bin python3-gdal

# Verify
python -c "from osgeo import gdal; print(gdal.__version__)"
```

---

### Issue 3: PostGIS Extension Not Found

**Error:**
```
django.db.utils.OperationalError: extension "postgis" does not exist
```

**Solution:**
```sql
-- Connect to database
psql georeach_db

-- Create extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify
SELECT PostGIS_Version();
```

---

### Issue 4: Duplicate Data

**Error:**
```
IntegrityError: duplicate key value violates unique constraint
```

**Solution:**
```bash
# Clear existing data
python manage.py shell

# In Python:
from geo.models import *
State.objects.all().delete()
District.objects.all().delete()

# Reload data
python load_real_shapefiles.py
python check_and_populate_data.py
```

---

### Issue 5: Missing Districts for State

**Error:**
```
No districts found for Maharashtra
```

**Solution:**
```python
# Check district-state links
from geo.models import State, District

state = State.objects.get(name='Maharashtra')
print(f"Districts: {state.districts.count()}")

# Reload if needed
python load_real_shapefiles.py
```

---

## 📊 Data Statistics

### Geographic Data

| Region | Count | Source |
|--------|-------|--------|
| States | 37 | GADM India Level 1 |
| Districts | 670+ | GADM India Level 2 |
| Total Geometries | 707 | MultiPolygon (SRID 4326) |

### Economic & Demographic Data

| Dataset | Records | Coverage |
|---------|---------|----------|
| Economic Indicators | 8 | Major states, urban/rural |
| Demographic Profiles | 45 | All age groups, tiers |
| Industry Employment | 30 | 10 industries |
| Market Zones | 3 | High/Medium/Low |

### Data Completeness

| Field | Coverage | Notes |
|-------|----------|-------|
| State boundaries | 100% | All 37 states |
| District boundaries | 100% | 670+ districts |
| Population data | ~80% | Most populated areas |
| Economic data | ~60% | Major urban centers |
| Demographics | ~70% | Tier 1/2 cities |

---

## 🎯 Next Steps After Loading Data

1. **Train ML Models:**
   ```bash
   python manage.py train_models
   ```

2. **Test Predictions:**
   - Visit http://127.0.0.1:8000/core/dashboard/entrepreneur/
   - Submit a prediction request
   - Verify results on map

3. **Explore APIs:**
   - Test all endpoints
   - Check GeoJSON responses
   - Verify spatial queries

4. **Customize Data:**
   - Add more economic indicators
   - Update demographics
   - Add custom market zones

---

## 📝 Data Refresh Procedure

To refresh/update data:

```bash
# 1. Backup current data (optional)
python manage.py dumpdata geo > backup_geo.json

# 2. Clear old data
python manage.py shell -c "from geo.models import *; EconomicIndicator.objects.all().delete(); DemographicProfile.objects.all().delete()"

# 3. Reload fresh data
python check_and_populate_data.py

# 4. Verify
python check_all_functionalities.py
```

---

## 🔗 Related Documentation

- **[COMPLETE_FUNCTIONALITY_LIST.md](COMPLETE_FUNCTIONALITY_LIST.md)** - All features
- **[API_URL_MAP.md](API_URL_MAP.md)** - API endpoints
- **[POSTGIS_QUERIES_GUIDE.md](POSTGIS_QUERIES_GUIDE.md)** - Spatial queries
- **[FIRST_DOWNLOAD_SETUP.md](FIRST_DOWNLOAD_SETUP.md)** - Initial setup

---

**Last Updated:** October 17, 2025  
**Data Version:** 1.0  
**Status:** Production Ready ✅
