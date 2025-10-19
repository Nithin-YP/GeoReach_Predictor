# 🚀 GeoReach Predictor - First Download Setup Guide

**Welcome!** This guide will help you set up GeoReach Predictor from scratch after downloading from GitHub.

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Prerequisites Installation](#prerequisites-installation)
3. [Project Setup](#project-setup)
4. [Database Configuration](#database-configuration)
5. [Running the Application](#running-the-application)
6. [First Login](#first-login)
7. [Troubleshooting](#troubleshooting)
8. [Next Steps](#next-steps)

---

## 💻 System Requirements

### Minimum Requirements
- **OS:** Windows 10/11, macOS 11+, Ubuntu 20.04+
- **RAM:** 4GB (8GB recommended)
- **Disk Space:** 5GB free space
- **Internet:** Required for downloading dependencies

### Software Requirements
- **Python:** 3.10 or higher
- **PostgreSQL:** 14 or higher
- **PostGIS:** 3.3 or higher
- **Git:** Latest version

---

## 🔧 Prerequisites Installation

### Step 1: Install Python 3.10+

#### Windows
1. Download from [python.org](https://www.python.org/downloads/)
2. Run installer, **check "Add Python to PATH"**
3. Verify:
```powershell
python --version
```

#### macOS
```bash
brew install python@3.10
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip
```

---

### Step 2: Install PostgreSQL + PostGIS

#### Windows
1. Download PostgreSQL 14+ from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run installer:
   - Set password for `postgres` user (remember this!)
   - Default port: 5432
3. Install PostGIS:
   - Use Stack Builder (included with PostgreSQL)
   - Select PostgreSQL 14 → Spatial Extensions → PostGIS 3.3

**Verify Installation:**
```powershell
psql --version
```

#### macOS
```bash
# Install PostgreSQL
brew install postgresql@14

# Install PostGIS
brew install postgis

# Start PostgreSQL
brew services start postgresql@14
```

#### Linux (Ubuntu/Debian)
```bash
# Install PostgreSQL and PostGIS
sudo apt update
sudo apt install postgresql-14 postgresql-14-postgis-3

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

### Step 3: Install GDAL (Geospatial Library)

GDAL is required for Django GIS features.

#### Windows
1. Download OSGeo4W installer from [trac.osgeo.org](https://trac.osgeo.org/osgeo4w/)
2. Run installer, select:
   - GDAL
   - PROJ
   - GEOS
3. Add to PATH:
```powershell
# Add to System Environment Variables:
C:\OSGeo4W64\bin
```

#### macOS
```bash
brew install gdal
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt install gdal-bin libgdal-dev
sudo apt install binutils libproj-dev
```

**Verify GDAL:**
```bash
gdalinfo --version
```

---

## 📦 Project Setup

### Step 1: Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/Strange-0007/GeoReach_Predictor.git
cd GeoReach_Predictor
```

---

### Step 2: Create Virtual Environment

#### Windows (PowerShell)
```powershell
# Create virtual environment
python -m venv venv

# Activate
.\venv\Scripts\Activate.ps1

# If you get execution policy error:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### macOS/Linux
```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate
```

**You should see `(venv)` in your terminal prompt.**

---

### Step 3: Install Python Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install all requirements
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed Django-5.2.7 psycopg2-binary-2.9.9 ...
```

**If GDAL installation fails:**
```bash
# Windows: Install from wheel
pip install GDAL-3.4.3-cp310-cp310-win_amd64.whl

# macOS/Linux: Use system GDAL
pip install GDAL==$(gdal-config --version)
```

---

## 🗄️ Database Configuration

### Step 1: Create PostgreSQL Database

#### Windows/macOS/Linux
```bash
# Open PostgreSQL command line
psql -U postgres

# Enter your PostgreSQL password
```

**In psql prompt:**
```sql
-- Create database
CREATE DATABASE georeach_db;

-- Create user (optional, recommended for production)
CREATE USER georeach_user WITH PASSWORD 'your_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE georeach_db TO georeach_user;

-- Enable PostGIS extension
\c georeach_db
CREATE EXTENSION postgis;

-- Verify PostGIS
SELECT PostGIS_Version();

-- Exit
\q
```

**Expected output:**
```
CREATE DATABASE
CREATE ROLE
GRANT
CREATE EXTENSION
    postgis_version    
-----------------------
 3.3 USE_GEOS=1 USE_PROJ...
```

---

### Step 2: Configure Django Settings

1. **Create `.env` file** (in project root):
```bash
# Copy example
cp .env.example .env
```

2. **Edit `.env` file:**
```env
# Database Configuration
DB_NAME=georeach_db
DB_USER=postgres
DB_PASSWORD=your_postgres_password
DB_HOST=localhost
DB_PORT=5432

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# GDAL Library Path (Windows only)
GDAL_LIBRARY_PATH=C:\OSGeo4W64\bin\gdal304.dll
GEOS_LIBRARY_PATH=C:\OSGeo4W64\bin\geos_c.dll
```

**Generate SECRET_KEY:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### Step 3: Run Database Migrations

```bash
# Apply migrations
python manage.py migrate

# Expected output:
# Running migrations:
#   Applying contenttypes.0001_initial... OK
#   Applying core.0001_initial... OK
#   Applying geo.0001_initial... OK
#   ...
```

**If successful, you should see:**
```
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, core, geo, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  ...
✅ All migrations completed!
```

---

### Step 4: Load Geographic Data

```bash
# Load India states and districts shapefiles
python geo/management/commands/load_geodata.py

# Expected output:
# Loading states from datasets/geodata/india_states.shp...
# Loaded 37 states
# Loading districts from datasets/geodata/india_districts.shp...
# Loaded 670 districts
# ✅ Geographic data loaded successfully!
```

---

### Step 5: Load Economic & Demographic Data

```bash
# Load CSV datasets
python scripts/data_loading.py

# Expected output:
# Loading economic indicators...
# Loaded 45 profiles
# Loading employment data...
# Loaded 30 employment records
# ✅ All datasets loaded!
```

---

### Step 6: Create Admin User

```bash
# Create superuser
python manage.py createsuperuser

# Enter details:
# Username: admin
# Email: admin@example.com
# Password: adminpassword (or your choice)
# Password (again): adminpassword
```

**Or use automated script:**
```bash
python core/management/commands/create_admin.py
```

---

## ▶️ Running the Application

### Step 1: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

### Step 2: Run Development Server

```bash
python manage.py runserver
```

**Expected output:**
```
Watching for file changes with StatReloader
Performing system checks...

System check identified no issues (0 silenced).
January 17, 2025 - 10:30:00
Django version 5.2.7, using settings 'georeach_predictor.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

---

### Step 3: Open in Browser

Navigate to:
```
http://localhost:8000/
```

**You should see the GeoReach Predictor homepage!** 🎉

---

## 🔐 First Login

### Admin Dashboard

1. Navigate to: `http://localhost:8000/core/login/`
2. Enter credentials:
   - **Username:** `admin`
   - **Password:** `adminpassword` (or what you set)
3. Click **Login**
4. You'll be redirected to **Admin Dashboard**

### Admin Features
- **User Management:** View/block users
- **Dataset Management:** Upload new datasets
- **System Health:** Check PostGIS status
- **Market Zones:** Manage high-potential zones

---

### Register as Entrepreneur

1. Navigate to: `http://localhost:8000/core/register/entrepreneur/`
2. Fill form:
   - Username
   - Email
   - Password
   - Business name
   - Product type
3. Login and access **Entrepreneur Dashboard**

### Entrepreneur Features
- **Market Predictions:** Get market reach predictions
- **GIS Tools:** Analyze market corridors
- **Demographics:** View population/income data
- **Spatial Queries:** Find districts within radius

---

## 🗺️ Test PostGIS Features

### 1. View Interactive Map

Navigate to:
```
http://localhost:8000/geo/map/
```

**Features:**
- Interactive India map with states/districts
- Click states to see details
- Population, area, demographic data
- GeoJSON layers

---

### 2. Test Spatial Queries

#### Find Districts Near Point (Mumbai)
```
GET http://localhost:8000/geo/api/nearby-districts/?lat=19.0760&lng=72.8777&radius=50
```

**Expected Response:**
```json
{
  "districts": [
    {"name": "Mumbai", "distance_km": 0.0},
    {"name": "Thane", "distance_km": 25.3},
    {"name": "Raigad", "distance_km": 45.8}
  ]
}
```

#### Analyze Market Corridor
```
POST http://localhost:8000/geo/api/analyze-corridor/
Content-Type: application/json

{
  "start_lat": 19.0760,
  "start_lng": 72.8777,
  "end_lat": 18.5204,
  "end_lng": 73.8567,
  "buffer_km": 20
}
```

---

## 🐛 Troubleshooting

### Issue 1: GDAL Import Error

**Error:**
```
OSError: [WinError 126] The specified module could not be found
```

**Solution (Windows):**
```python
# Edit georeach_predictor/settings.py
# Add GDAL path before DATABASES config:

if os.name == 'nt':  # Windows
    GDAL_LIBRARY_PATH = r'C:\OSGeo4W64\bin\gdal304.dll'
    GEOS_LIBRARY_PATH = r'C:\OSGeo4W64\bin\geos_c.dll'
```

---

### Issue 2: PostgreSQL Connection Error

**Error:**
```
django.db.utils.OperationalError: could not connect to server
```

**Solutions:**
1. Check PostgreSQL is running:
   ```bash
   # Windows
   services.msc → PostgreSQL → Start
   
   # macOS
   brew services start postgresql@14
   
   # Linux
   sudo systemctl start postgresql
   ```

2. Verify credentials in `.env`:
   ```env
   DB_USER=postgres
   DB_PASSWORD=your_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

3. Test connection:
   ```bash
   psql -U postgres -d georeach_db
   ```

---

### Issue 3: PostGIS Not Found

**Error:**
```
django.db.utils.ProgrammingError: type "geometry" does not exist
```

**Solution:**
```sql
-- Connect to database
psql -U postgres -d georeach_db

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verify
SELECT PostGIS_Version();
```

---

### Issue 4: Migration Errors

**Error:**
```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

**Solution:**
```bash
# Reset migrations (WARNING: This deletes data!)
python manage.py migrate --fake core zero
python manage.py migrate --fake geo zero
python manage.py migrate --fake

# Or start fresh:
DROP DATABASE georeach_db;
CREATE DATABASE georeach_db;
\c georeach_db
CREATE EXTENSION postgis;
```

---

### Issue 5: Admin Can't Login

**Error:** Invalid credentials

**Solution:**
```bash
# Reset admin password
python manage.py shell

# In Python shell:
from core.models import User
admin = User.objects.get(username='admin')
admin.set_password('adminpassword')
admin.save()
exit()
```

---

### Issue 6: Static Files Not Loading

**Error:** CSS/JS not loading (404 errors)

**Solution:**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify STATIC_ROOT in settings.py:
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'
```

---

### Issue 7: CSRF Verification Failed

**Error:** CSRF token missing or incorrect

**Solution:**
1. Check `{% csrf_token %}` in all forms
2. Verify middleware in settings.py:
   ```python
   MIDDLEWARE = [
       'django.middleware.csrf.CsrfViewMiddleware',
       ...
   ]
   ```
3. Clear browser cookies and retry

**For API testing:**
```bash
# Run CSRF test
python test_csrf.py
```

---

## 📚 Next Steps

### 1. Explore Documentation

- **[Complete Functionality List](COMPLETE_FUNCTIONALITY_LIST.md)** - All 19 features
- **[API URL Map](API_URL_MAP.md)** - 32 endpoints with examples
- **[PostGIS Queries Guide](POSTGIS_QUERIES_GUIDE.md)** - Spatial query examples
- **[Data Loading Guide](SYNTHETIC_DATA_LOADING_GUIDE.md)** - Load additional datasets

---

### 2. Train ML Models

```bash
# Train prediction models
python core/management/commands/train_models.py

# Expected output:
# Training Random Forest model...
# Model accuracy: 85.3%
# Saved to core/models_ml/market_predictor.pkl
```

---

### 3. Test All APIs

```bash
# Run comprehensive API test
python test_postgis_apis.py

# Expected output:
# Testing 32 endpoints...
# ✅ All tests passed!
```

---

### 4. Customize for Your Use Case

#### Add Custom Market Zones
```python
# In Django shell
python manage.py shell

from geo.models import MarketPotentialZone, District
district = District.objects.get(name='Mumbai')
MarketPotentialZone.objects.create(
    district=district,
    product_type='Premium Smartphone',
    potential_level='HIGH',
    market_score=95.5,
    estimated_target_population=5000000
)
```

#### Add Custom Datasets
1. Place CSV in `datasets/`
2. Create migration script in `scripts/data_loading.py`
3. Run: `python scripts/data_loading.py`

---

### 5. Deploy to Production

See [DEPLOYMENT.md](DEPLOYMENT.md) for:
- Production settings (`DEBUG=False`)
- Environment variables
- HTTPS configuration
- Database backup strategies
- Nginx/Apache setup

---

## 🎯 Quick Start Checklist

- [ ] Python 3.10+ installed
- [ ] PostgreSQL 14+ installed
- [ ] PostGIS 3.3+ installed
- [ ] GDAL installed
- [ ] Repository cloned
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file configured
- [ ] Database created (`CREATE DATABASE georeach_db`)
- [ ] PostGIS enabled (`CREATE EXTENSION postgis`)
- [ ] Migrations applied (`python manage.py migrate`)
- [ ] Geographic data loaded (`load_geodata.py`)
- [ ] Economic data loaded (`data_loading.py`)
- [ ] Admin user created (`createsuperuser`)
- [ ] Server running (`runserver`)
- [ ] Accessed at `http://localhost:8000/`
- [ ] Admin login successful
- [ ] Map displaying correctly
- [ ] API endpoints working

---

## 🆘 Get Help

### Resources
- **GitHub Issues:** [Report bugs](https://github.com/Strange-0007/GeoReach_Predictor/issues)
- **Django Docs:** [docs.djangoproject.com](https://docs.djangoproject.com/)
- **PostGIS Docs:** [postgis.net/documentation](https://postgis.net/documentation/)

### Common Commands Reference

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\Activate.ps1  # Windows

# Run server
python manage.py runserver

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Check for errors
python manage.py check

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic
```

---

**🎉 Congratulations!** You've successfully set up GeoReach Predictor!

**Last Updated:** January 17, 2025  
**Version:** 1.0.0  
**Django:** 5.2.7 | **PostGIS:** 3.3+
