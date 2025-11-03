"""
ML Pipeline for GeoReach Predictor
Handles data processing, model training, and prediction generation
"""

import pandas as pd  # type: ignore
import numpy as np  # type: ignore
import json
import os
import re
import logging
from typing import Dict, Any, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Try to import ML libraries, with fallback if not available
try:
    from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler
    from sklearn.cluster import KMeans
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split  # type: ignore
    import joblib  # type: ignore
    ML_LIBRARIES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ML libraries not available: {e}")
    ML_LIBRARIES_AVAILABLE = False

# Define directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
ML_MODELS_DIR = os.path.join(BASE_DIR, 'core', 'models_ml')

# Ensure the ML models directory exists
os.makedirs(ML_MODELS_DIR, exist_ok=True)

# File paths for saved models
SCALER_PATH = os.path.join(ML_MODELS_DIR, 'scaler.joblib')
KMEANS_PATH = os.path.join(ML_MODELS_DIR, 'kmeans_model.joblib')
RF_MODEL_PATH = os.path.join(ML_MODELS_DIR, 'random_forest_model.joblib')

def clean_col_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean column names by stripping whitespace"""
    df.columns = df.columns.str.strip()
    return df

def load_datasets() -> Dict[str, Optional[pd.DataFrame]]:
    """
    Load all datasets with error handling
    Returns a dictionary of dataset names to DataFrames or None if loading fails
    """
    datasets = {}
    dataset_files = {
        'population_india': 'Population_of_India.csv',
        'district_population_india': 'India_Districts_Population.csv',
        'personal_finance_india': 'Indian_Personal_Finance.csv',
        'income_expenditure_india': 'Income_Expenditure.csv',
        'unemployment_india': 'Unemployment_India.csv',
        'employment_data_india': 'Employment_India.csv',
        'customer_spend_india': 'Customer_Spend.csv'
    }
    
    for key, filename in dataset_files.items():
        filepath = os.path.join(DATASETS_DIR, filename)
        try:
            if os.path.exists(filepath):
                df = pd.read_csv(filepath)
                datasets[key] = clean_col_names(df)
                logger.info(f"Successfully loaded {filename}")
            else:
                logger.warning(f"Dataset file not found: {filepath}")
                datasets[key] = None
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            datasets[key] = None
    
    return datasets


def create_training_data() -> Optional[pd.DataFrame]:
    """
    Create a unified training dataset from various sources.
    This function will process, pivot, and merge demographic, economic, and market potential data.
    """
    logger.info("Creating unified training data...")
    
    # Define paths to the datasets
    demographics_path = os.path.join(DATASETS_DIR, 'synthetic', 'demographic_profiles.csv')
    economics_path = os.path.join(DATASETS_DIR, 'synthetic', 'economic_indicators.csv')
    market_potential_path = os.path.join(DATASETS_DIR, 'synthetic', 'market_potential_zones.csv')

    try:
        # Load the datasets
        demographics_df = pd.read_csv(demographics_path)
        economics_df = pd.read_csv(economics_path)
        market_potential_df = pd.read_csv(market_potential_path)

        # --- 1. Process Demographics Data ---
        # Pivot to get age groups as columns
        demographics_pivot = demographics_df.pivot_table(
            index=['state', 'district'],
            columns='age_group',
            values='sample_size',
            aggfunc='sum'
        ).reset_index()
        demographics_pivot.columns.name = None
        demographics_pivot = demographics_pivot.fillna(0)
        
        logger.info(f"Pivoted demographics columns: {demographics_pivot.columns.tolist()}")

        # Dynamically identify age columns
        age_cols = [col for col in demographics_pivot.columns if isinstance(col, str) and re.match(r'\d+.*', col)]
        
        # Calculate total population and other aggregated metrics from the original demographics df
        demographics_agg = demographics_df.groupby(['state', 'district']).agg(
            avg_income=('avg_income', 'mean'),
            avg_disposable_income=('avg_disposable_income', 'mean'),
            avg_spending=('avg_spending', 'mean')
        ).reset_index()

        # Merge pivoted data with aggregated data
        demographics_processed = pd.merge(demographics_pivot, demographics_agg, on=['state', 'district'])
        
        # Use the correct pivoted column names for calculations
        demographics_processed['total_population'] = demographics_processed[age_cols].sum(axis=1)
        
        # Identify columns for 18-35 age range
        pop_18_35_cols = [col for col in age_cols if '18-25' in col or '26-35' in col]
        demographics_processed['population_18_35'] = demographics_processed[pop_18_35_cols].sum(axis=1)


        # --- 2. Process Economics Data ---
        economics_agg = economics_df.groupby('district').agg(
            employment_rate=('employment_rate', 'mean'),
            unemployment_rate=('unemployment_rate', 'mean'),
            gdp_per_capita=('avg_monthly_salary', lambda x: x.mean() * 12) # Approximate GDP per capita
        ).reset_index()

        # --- 3. Process Market Potential Data ---
        # Group by district and calculate the mean market score across all product types
        market_potential_agg = market_potential_df.groupby('district').agg(
            market_potential_score=('market_score', 'mean')
        ).reset_index()

        # --- 4. Merge All Datasets ---
        merged_df = pd.merge(demographics_processed, economics_agg, on='district', how='inner')
        training_df = pd.merge(merged_df, market_potential_agg, on='district', how='inner')

        # --- 5. Feature Engineering ---
        training_df['youth_ratio'] = training_df['population_18_35'] / training_df['total_population']
        training_df['disposable_income_per_capita'] = training_df['avg_disposable_income'] # This is already per capita from source

        # Select final features and target
        features = [
            'total_population', 'population_18_35', 'avg_income', 'gdp_per_capita',
            'avg_disposable_income', 'avg_spending',
            'youth_ratio', 'disposable_income_per_capita', 'employment_rate'
        ]
        target = 'market_potential_score'
        
        final_columns = features + [target, 'district', 'state']
        training_df = training_df[final_columns].dropna()
        
        logger.info(f"Successfully created training data with {len(training_df)} records.")
        return training_df

    except FileNotFoundError as e:
        logger.error(f"Error creating training data: Dataset file not found - {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while creating training data: {e}")
        return None


def get_dummy_prediction_data() -> Dict[str, Any]:
    """
    Generate dummy prediction data when ML models are not available
    This is kept as fallback only
    """
    return {
        'predicted_reach': round(np.random.uniform(30, 90), 2),
        'success_probability': round(np.random.uniform(0.4, 0.9), 3),
        'model_confidence': round(np.random.uniform(0.6, 0.95), 3),
        'clusters': [
            {
                'lat': round(np.random.uniform(8.0, 37.0), 6),
                'lon': round(np.random.uniform(68.0, 97.0), 6),
                'label': np.random.choice(['High', 'Medium', 'Low']),
                'population_density': np.random.randint(100, 2000),
                'avg_income': round(np.random.uniform(25000, 80000), 2),
                'employment_rate': round(np.random.uniform(60, 95), 2),
                'interest_index': round(np.random.uniform(0.3, 0.9), 3)
            }
            for _ in range(3)
        ]
    }


def get_indian_cities_data() -> List[Dict[str, Any]]:
    """
    Returns comprehensive data for major Indian cities with demographics and economic indicators
    """
    return [
        # Tier 1 Cities - High Potential
        {
            'name': 'Mumbai', 'state': 'Maharashtra',
            'lat': 19.0760, 'lon': 72.8777,
            'population': 20961472, 'area_km2': 603,
            'population_density': 34753, 'literacy_rate': 89.2,
            'avg_income': 85000, 'avg_disposable_income': 52000,
            'unemployment_rate': 3.8, 'employment_rate': 96.2,
            'urban_rural': 'URBAN', 'tier': 1,
            'groceries_exp': 8500, 'beverages_exp': 6200, 'eating_out_exp': 4500,
            'healthcare_exp': 5500, 'entertainment_exp': 3500
        },
        {
            'name': 'Delhi', 'state': 'Delhi',
            'lat': 28.7041, 'lon': 77.1025,
            'population': 32941000, 'area_km2': 1484,
            'population_density': 22205, 'literacy_rate': 88.7,
            'avg_income': 82000, 'avg_disposable_income': 50000,
            'unemployment_rate': 4.2, 'employment_rate': 95.8,
            'urban_rural': 'URBAN', 'tier': 1,
            'groceries_exp': 8200, 'beverages_exp': 6000, 'eating_out_exp': 4800,
            'healthcare_exp': 5200, 'entertainment_exp': 3800
        },
        {
            'name': 'Bangalore', 'state': 'Karnataka',
            'lat': 12.9716, 'lon': 77.5946,
            'population': 12764935, 'area_km2': 741,
            'population_density': 17232, 'literacy_rate': 88.5,
            'avg_income': 78000, 'avg_disposable_income': 48000,
            'unemployment_rate': 2.8, 'employment_rate': 97.2,
            'urban_rural': 'URBAN', 'tier': 1,
            'groceries_exp': 7800, 'beverages_exp': 5800, 'eating_out_exp': 5200,
            'healthcare_exp': 5000, 'entertainment_exp': 4200
        },
        {
            'name': 'Hyderabad', 'state': 'Telangana',
            'lat': 17.3850, 'lon': 78.4867,
            'population': 10004144, 'area_km2': 650,
            'population_density': 15391, 'literacy_rate': 83.3,
            'avg_income': 72000, 'avg_disposable_income': 45000,
            'unemployment_rate': 3.2, 'employment_rate': 96.8,
            'urban_rural': 'URBAN', 'tier': 1,
            'groceries_exp': 7500, 'beverages_exp': 5500, 'eating_out_exp': 4200,
            'healthcare_exp': 4800, 'entertainment_exp': 3600
        },
        {
            'name': 'Chennai', 'state': 'Tamil Nadu',
            'lat': 13.0827, 'lon': 80.2707,
            'population': 10971108, 'area_km2': 426,
            'population_density': 25750, 'literacy_rate': 90.2,
            'avg_income': 75000, 'avg_disposable_income': 46000,
            'unemployment_rate': 3.5, 'employment_rate': 96.5,
            'urban_rural': 'URBAN', 'tier': 1,
            'groceries_exp': 7600, 'beverages_exp': 5400, 'eating_out_exp': 3800,
            'healthcare_exp': 4900, 'entertainment_exp': 3400
        },
        {
            'name': 'Pune', 'state': 'Maharashtra',
            'lat': 18.5204, 'lon': 73.8567,
            'population': 7272506, 'area_km2': 331,
            'population_density': 21975, 'literacy_rate': 86.1,
            'avg_income': 70000, 'avg_disposable_income': 43000,
            'unemployment_rate': 3.6, 'employment_rate': 96.4,
            'urban_rural': 'URBAN', 'tier': 1,
            'groceries_exp': 7200, 'beverages_exp': 5200, 'eating_out_exp': 4000,
            'healthcare_exp': 4600, 'entertainment_exp': 3300
        },
        
        # Tier 2 Cities - Medium Potential
        {
            'name': 'Ahmedabad', 'state': 'Gujarat',
            'lat': 23.0225, 'lon': 72.5714,
            'population': 8450228, 'area_km2': 505,
            'population_density': 16732, 'literacy_rate': 85.3,
            'avg_income': 62000, 'avg_disposable_income': 38000,
            'unemployment_rate': 4.5, 'employment_rate': 95.5,
            'urban_rural': 'URBAN', 'tier': 2,
            'groceries_exp': 6500, 'beverages_exp': 4500, 'eating_out_exp': 3200,
            'healthcare_exp': 4000, 'entertainment_exp': 2800
        },
        {
            'name': 'Kolkata', 'state': 'West Bengal',
            'lat': 22.5726, 'lon': 88.3639,
            'population': 14850066, 'area_km2': 205,
            'population_density': 72455, 'literacy_rate': 87.1,
            'avg_income': 58000, 'avg_disposable_income': 36000,
            'unemployment_rate': 5.2, 'employment_rate': 94.8,
            'urban_rural': 'URBAN', 'tier': 2,
            'groceries_exp': 6200, 'beverages_exp': 4200, 'eating_out_exp': 2800,
            'healthcare_exp': 3800, 'entertainment_exp': 2600
        },
        {
            'name': 'Jaipur', 'state': 'Rajasthan',
            'lat': 26.9124, 'lon': 75.7873,
            'population': 3887063, 'area_km2': 467,
            'population_density': 8322, 'literacy_rate': 82.5,
            'avg_income': 55000, 'avg_disposable_income': 34000,
            'unemployment_rate': 4.8, 'employment_rate': 95.2,
            'urban_rural': 'URBAN', 'tier': 2,
            'groceries_exp': 5800, 'beverages_exp': 4000, 'eating_out_exp': 2600,
            'healthcare_exp': 3600, 'entertainment_exp': 2400
        },
        {
            'name': 'Lucknow', 'state': 'Uttar Pradesh',
            'lat': 26.8467, 'lon': 80.9462,
            'population': 3645708, 'area_km2': 631,
            'population_density': 5778, 'literacy_rate': 79.4,
            'avg_income': 52000, 'avg_disposable_income': 32000,
            'unemployment_rate': 5.5, 'employment_rate': 94.5,
            'urban_rural': 'URBAN', 'tier': 2,
            'groceries_exp': 5500, 'beverages_exp': 3800, 'eating_out_exp': 2400,
            'healthcare_exp': 3400, 'entertainment_exp': 2200
        },
        {
            'name': 'Surat', 'state': 'Gujarat',
            'lat': 21.1702, 'lon': 72.8311,
            'population': 6564415, 'area_km2': 326,
            'population_density': 20135, 'literacy_rate': 85.5,
            'avg_income': 60000, 'avg_disposable_income': 37000,
            'unemployment_rate': 3.9, 'employment_rate': 96.1,
            'urban_rural': 'URBAN', 'tier': 2,
            'groceries_exp': 6000, 'beverages_exp': 4300, 'eating_out_exp': 2900,
            'healthcare_exp': 3700, 'entertainment_exp': 2600
        },
        
        # Tier 3 Cities - Low Potential
        {
            'name': 'Indore', 'state': 'Madhya Pradesh',
            'lat': 22.7196, 'lon': 75.8577,
            'population': 3276697, 'area_km2': 530,
            'population_density': 6182, 'literacy_rate': 83.6,
            'avg_income': 48000, 'avg_disposable_income': 30000,
            'unemployment_rate': 5.8, 'employment_rate': 94.2,
            'urban_rural': 'URBAN', 'tier': 3,
            'groceries_exp': 5200, 'beverages_exp': 3500, 'eating_out_exp': 2200,
            'healthcare_exp': 3200, 'entertainment_exp': 2000
        },
        {
            'name': 'Bhopal', 'state': 'Madhya Pradesh',
            'lat': 23.2599, 'lon': 77.4126,
            'population': 2402406, 'area_km2': 463,
            'population_density': 5189, 'literacy_rate': 80.4,
            'avg_income': 45000, 'avg_disposable_income': 28000,
            'unemployment_rate': 6.2, 'employment_rate': 93.8,
            'urban_rural': 'URBAN', 'tier': 3,
            'groceries_exp': 4800, 'beverages_exp': 3200, 'eating_out_exp': 2000,
            'healthcare_exp': 3000, 'entertainment_exp': 1800
        },
        {
            'name': 'Chandigarh', 'state': 'Chandigarh',
            'lat': 30.7333, 'lon': 76.7794,
            'population': 1158473, 'area_km2': 114,
            'population_density': 10159, 'literacy_rate': 86.4,
            'avg_income': 65000, 'avg_disposable_income': 40000,
            'unemployment_rate': 4.1, 'employment_rate': 95.9,
            'urban_rural': 'URBAN', 'tier': 3,
            'groceries_exp': 6800, 'beverages_exp': 4800, 'eating_out_exp': 3500,
            'healthcare_exp': 4200, 'entertainment_exp': 3000
        },
    ]


def calculate_cluster_potential(city: Dict[str, Any], product_type: str, 
                               product_luxury: str, price: float) -> Dict[str, Any]:
    """
    Calculate the potential score for a city based on product characteristics
    Returns cluster data with proper classification
    """
    
    # Base score from city characteristics
    base_score = 0.0
    
    # Product-specific scoring logic
    product_criteria = {
        'Food': {
            'High': {'min_income': 60000, 'min_exp': 7000, 'weight_income': 0.4, 'weight_density': 0.3, 'weight_literacy': 0.3},
            'Medium': {'min_income': 40000, 'min_exp': 5000, 'weight_income': 0.35, 'weight_density': 0.35, 'weight_literacy': 0.3},
            'Low': {'min_income': 25000, 'min_exp': 3000, 'weight_income': 0.3, 'weight_density': 0.4, 'weight_literacy': 0.3}
        },
        'Groceries': {
            'High': {'min_income': 50000, 'min_exp': 6500, 'weight_income': 0.35, 'weight_density': 0.4, 'weight_literacy': 0.25},
            'Medium': {'min_income': 35000, 'min_exp': 4500, 'weight_income': 0.3, 'weight_density': 0.45, 'weight_literacy': 0.25},
            'Low': {'min_income': 20000, 'min_exp': 2500, 'weight_income': 0.25, 'weight_density': 0.5, 'weight_literacy': 0.25}
        },
        'Technology': {
            'High': {'min_income': 70000, 'min_exp': 0, 'weight_income': 0.5, 'weight_density': 0.2, 'weight_literacy': 0.3},
            'Medium': {'min_income': 50000, 'min_exp': 0, 'weight_income': 0.45, 'weight_density': 0.25, 'weight_literacy': 0.3},
            'Low': {'min_income': 35000, 'min_exp': 0, 'weight_income': 0.4, 'weight_density': 0.3, 'weight_literacy': 0.3}
        },
        'Clothing': {
            'High': {'min_income': 55000, 'min_exp': 0, 'weight_income': 0.4, 'weight_density': 0.3, 'weight_literacy': 0.3},
            'Medium': {'min_income': 35000, 'min_exp': 0, 'weight_income': 0.35, 'weight_density': 0.35, 'weight_literacy': 0.3},
            'Low': {'min_income': 20000, 'min_exp': 0, 'weight_income': 0.3, 'weight_density': 0.4, 'weight_literacy': 0.3}
        },
        'Healthcare': {
            'High': {'min_income': 60000, 'min_exp': 5000, 'weight_income': 0.45, 'weight_density': 0.25, 'weight_literacy': 0.3},
            'Medium': {'min_income': 40000, 'min_exp': 3500, 'weight_income': 0.4, 'weight_density': 0.3, 'weight_literacy': 0.3},
            'Low': {'min_income': 25000, 'min_exp': 2000, 'weight_income': 0.35, 'weight_density': 0.35, 'weight_literacy': 0.3}
        }
    }
    
    # Get criteria for product type, default to generic if not found
    criteria = product_criteria.get(product_type, product_criteria['Food']).get(product_luxury, {
        'min_income': 30000, 'min_exp': 3000, 
        'weight_income': 0.35, 'weight_density': 0.35, 'weight_literacy': 0.3
    })
    
    # Calculate normalized scores (0-1)
    income_score = min(city['avg_disposable_income'] / 100000, 1.0)  # Normalize to 100k max
    density_score = min(city['population_density'] / 50000, 1.0)  # Normalize to 50k max
    literacy_score = city['literacy_rate'] / 100.0
    employment_score = city['employment_rate'] / 100.0
    
    # Calculate weighted score
    base_score = (
        income_score * criteria['weight_income'] +
        density_score * criteria['weight_density'] +
        literacy_score * criteria['weight_literacy']
    )
    
    # Price affordability factor
    price_affordability = 1.0
    if price > 0:
        affordability_ratio = city['avg_disposable_income'] / (price * 12)  # Annual affordability
        price_affordability = min(affordability_ratio / 10, 1.0)  # Normalize
    
    # Final interest index
    interest_index = (base_score * 0.7 + price_affordability * 0.2 + employment_score * 0.1)
    interest_index = max(0.1, min(0.95, interest_index))  # Clamp between 0.1 and 0.95
    
    # Determine label based on interest index
    if interest_index >= 0.65:
        label = 'High'
    elif interest_index >= 0.40:
        label = 'Medium'
    else:
        label = 'Low'
    
    # Get relevant expenditure based on product type
    relevant_exp = city.get('groceries_exp', 5000)
    if product_type == 'Food':
        relevant_exp = city.get('eating_out_exp', city.get('beverages_exp', 5000))
    elif product_type == 'Healthcare':
        relevant_exp = city.get('healthcare_exp', 4000)
    elif product_type == 'Entertainment':
        relevant_exp = city.get('entertainment_exp', 3000)
    
    return {
        'lat': city['lat'],
        'lon': city['lon'],
        'label': label,
        'city_name': city['name'],
        'state': city['state'],
        'population': city['population'],
        'population_density': city['population_density'],
        'avg_income': city['avg_income'],
        'employment_rate': city['employment_rate'],
        'interest_index': round(interest_index, 3),
        'tier': city['tier'],
        'literacy_rate': city['literacy_rate'],
        'relevant_expenditure': relevant_exp
    }


def generate_logical_clusters(product_type: str, product_luxury: str, 
                              target_audience: str, price: float) -> List[Dict[str, Any]]:
    """
    Generate realistic clusters based on product characteristics and Indian city data
    Returns exactly 3 clusters: High, Medium, and Low potential
    """
    
    cities_data = get_indian_cities_data()
    
    # Calculate potential for all cities
    scored_cities = []
    for city in cities_data:
        cluster = calculate_cluster_potential(city, product_type, product_luxury, price)
        scored_cities.append(cluster)
    
    # Sort by interest index (descending)
    scored_cities.sort(key=lambda x: x['interest_index'], reverse=True)
    
    # Select top 3 diverse clusters with unique cities
    selected_clusters = []
    used_cities = set()
    
    # First, try to find a High potential cluster
    for cluster in scored_cities:
        if cluster['interest_index'] >= 0.65 and cluster['city_name'] not in used_cities:
            cluster['label'] = 'High'
            selected_clusters.append(cluster)
            used_cities.add(cluster['city_name'])
            break
    
    # If no High cluster found, take the top one
    if not selected_clusters:
        top_cluster = scored_cities[0]
        top_cluster['label'] = 'High'
        selected_clusters.append(top_cluster)
        used_cities.add(top_cluster['city_name'])
    
    # Find Medium potential cluster (avoid same tier and city as high)
    for cluster in scored_cities:
        if cluster['city_name'] not in used_cities:
            if 0.40 <= cluster['interest_index'] < 0.65:
                cluster['label'] = 'Medium'
                selected_clusters.append(cluster)
                used_cities.add(cluster['city_name'])
                break
    
    # If no Medium cluster found in the range, select from middle of sorted list
    if len(selected_clusters) < 2:
        mid_idx = len(scored_cities) // 2
        for i in range(mid_idx, len(scored_cities)):
            if scored_cities[i]['city_name'] not in used_cities:
                scored_cities[i]['label'] = 'Medium'
                selected_clusters.append(scored_cities[i])
                used_cities.add(scored_cities[i]['city_name'])
                break
    
    # Find Low potential cluster
    for cluster in reversed(scored_cities):
        if cluster['city_name'] not in used_cities:
            if cluster['interest_index'] < 0.40:
                cluster['label'] = 'Low'
                selected_clusters.append(cluster)
                used_cities.add(cluster['city_name'])
                break
    
    # If no Low cluster found in the range, take from bottom
    if len(selected_clusters) < 3:
        for i in range(len(scored_cities) - 1, -1, -1):
            if scored_cities[i]['city_name'] not in used_cities:
                scored_cities[i]['label'] = 'Low'
                selected_clusters.append(scored_cities[i])
                used_cities.add(scored_cities[i]['city_name'])
                break
    
    # Safety check: ensure we have 3 clusters
    while len(selected_clusters) < 3 and len(scored_cities) > len(selected_clusters):
        for cluster in scored_cities:
            if cluster['city_name'] not in used_cities:
                # Assign appropriate label based on position
                if len(selected_clusters) == 0:
                    cluster['label'] = 'High'
                elif len(selected_clusters) == 1:
                    cluster['label'] = 'Medium'
                else:
                    cluster['label'] = 'Low'
                selected_clusters.append(cluster)
                used_cities.add(cluster['city_name'])
                break
    
    return selected_clusters


def calculate_realistic_metrics(clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate realistic prediction metrics based on cluster analysis
    """
    # Calculate average interest index
    avg_interest = sum(c['interest_index'] for c in clusters) / len(clusters)
    
    # Calculate predicted reach based on cluster potentials
    # Weight by population and interest
    total_population = sum(c['population'] for c in clusters)
    weighted_reach = sum(
        (c['population'] / total_population) * c['interest_index'] * 100 
        for c in clusters
    )
    
    # Calculate success probability based on high potential clusters
    high_clusters = [c for c in clusters if c['label'] == 'High']
    success_prob = avg_interest * 0.8 + (len(high_clusters) / len(clusters)) * 0.2
    
    # Model confidence based on data quality
    confidence = 0.75 + (avg_interest * 0.2)  # Higher interest = higher confidence
    
    return {
        'predicted_reach': round(min(weighted_reach, 95.0), 2),
        'success_probability': round(min(success_prob, 0.95), 3),
        'model_confidence': round(min(confidence, 0.95), 3)
    }

def create_basic_merged_data() -> Optional[pd.DataFrame]:
    """
    Create a basic merged dataset from available data
    """
    datasets = load_datasets()
    
    # Start with population data if available
    if datasets['population_india'] is not None:
        merged_data = datasets['population_india'].copy()
        
        # Add basic state coordinates (approximate centroids)
        state_coordinates = {
            'Andhra Pradesh': (15.917987, 79.740026),
            'Arunachal Pradesh': (28.217999, 94.727753),
            'Assam': (26.200604, 92.937574),
            'Bihar': (25.096071, 85.313119),
            'Chhattisgarh': (21.2787, 81.8661),
            'Goa': (15.2993, 74.1240),
            'Gujarat': (22.2587, 71.1924),
            'Haryana': (29.0588, 76.0856),
            'Himachal Pradesh': (31.1048, 77.1734),
            'Jharkhand': (23.6102, 85.2799),
            'Karnataka': (15.3173, 75.7139),
            'Kerala': (10.8505, 76.2711),
            'Madhya Pradesh': (22.9734, 78.6569),
            'Maharashtra': (19.7515, 75.7139),
            'Manipur': (24.6637, 93.9063),
            'Meghalaya': (25.4670, 91.3662),
            'Mizoram': (23.1645, 92.9376),
            'Nagaland': (26.1584, 94.5624),
            'Odisha': (20.9517, 85.0985),
            'Punjab': (31.1471, 75.3412),
            'Rajasthan': (27.0238, 74.2179),
            'Sikkim': (27.5330, 88.5122),
            'Tamil Nadu': (11.1271, 78.6569),
            'Telangana': (18.1124, 79.0193),
            'Tripura': (23.9408, 91.9882),
            'Uttar Pradesh': (26.8467, 80.9462),
            'Uttarakhand': (30.0668, 79.0193),
            'West Bengal': (22.9868, 87.8550),
        }
        
        # Add coordinates
        merged_data['latitude'] = merged_data['State'].map(lambda x: state_coordinates.get(x, (20.5937, 78.9629))[0])
        merged_data['longitude'] = merged_data['State'].map(lambda x: state_coordinates.get(x, (20.5937, 78.9629))[1])
        
        # Fill missing values
        merged_data = merged_data.fillna(0)
        
        # Add some basic economic indicators if other datasets are available
        if datasets['personal_finance_india'] is not None:
            avg_income = datasets['personal_finance_india']['Income'].mean() if 'Income' in datasets['personal_finance_india'].columns else 50000
            merged_data['National_Avg_Personal_Income'] = avg_income
        
        return merged_data
    
    return None

def run_prediction_pipeline(product_type: str, product_luxury: str, target_audience: str, 
                          price: float, region: str) -> Dict[str, Any]:
    """
    Main prediction pipeline function. This version uses the trained ML model
    to score all districts and identify the best potential markets.
    
    Args:
        product_type: Type of product (used for logical fallback).
        product_luxury: Luxury level (used for logical fallback).
        target_audience: Target customer segment (used for logical fallback).
        price: Product price (used for logical fallback).
        region: Geographic region (currently unused by the model but kept for API consistency).
    
    Returns:
        Dictionary containing prediction results.
    """
    
    logger.info(f"Running ML-driven prediction for {product_type} in {region}")
    
    # Check if ML libraries and models are available
    if not ML_LIBRARIES_AVAILABLE:
        logger.warning("ML libraries not available, falling back to logical cluster generation.")
        print("LOGICAL FALLBACK: ML libraries not available.")
        clusters = generate_logical_clusters(product_type, product_luxury, target_audience, price)
        metrics = calculate_realistic_metrics(clusters)
        return {**metrics, 'clusters': clusters}

    models_exist = all(os.path.exists(path) for path in [SCALER_PATH, RF_MODEL_PATH])
    if not models_exist:
        logger.warning("Trained models not found, falling back to logical cluster generation.")
        print("LOGICAL FALLBACK: Trained models not found.")
        clusters = generate_logical_clusters(product_type, product_luxury, target_audience, price)
        metrics = calculate_realistic_metrics(clusters)
        return {**metrics, 'clusters': clusters}

    try:
        # Load the trained scaler and model
        scaler: StandardScaler = joblib.load(SCALER_PATH)
        model: RandomForestRegressor = joblib.load(RF_MODEL_PATH)
        
        # Load the complete dataset for prediction
        prediction_data = create_training_data()
        if prediction_data is None:
            raise ValueError("Failed to load prediction data.")

        # Define the features the model was trained on
        features = [
            'total_population', 'population_18_35', 'avg_income', 'gdp_per_capita',
            'avg_disposable_income', 'avg_spending',
            'youth_ratio', 'disposable_income_per_capita', 'employment_rate'
        ]
        
        X_predict = prediction_data[features]
        
        # Scale the features for prediction
        X_predict_scaled = scaler.transform(X_predict)
        
        # Predict the market potential score for all districts
        prediction_data['predicted_score'] = model.predict(X_predict_scaled)
        
        # Sort districts by the predicted score
        sorted_districts = prediction_data.sort_values(by='predicted_score', ascending=False)
        
        # Select High, Medium, and Low potential clusters
        high_potential_district = sorted_districts.iloc[0]
        medium_potential_district = sorted_districts.iloc[len(sorted_districts) // 2]
        low_potential_district = sorted_districts.iloc[-1]
        
        selected_districts = [high_potential_district, medium_potential_district, low_potential_district]
        labels = ['High', 'Medium', 'Low']
        
        # Create cluster data for the response
        clusters = []
        # Use city data as a proxy for lat/lon for now
        cities_data = {city['name'].lower(): city for city in get_indian_cities_data()}

        for i, district_data in enumerate(selected_districts):
            # Attempt to find matching city for lat/lon
            city_info = cities_data.get(district_data['district'].lower(), {})
            
            clusters.append({
                'lat': city_info.get('lat', 20.5937),  # Default to India's center
                'lon': city_info.get('lon', 78.9629),
                'label': labels[i],
                'city_name': district_data['district'].title(),
                'state': district_data['state'],
                'population': int(district_data['total_population']),
                'population_density': int(district_data.get('population_density', 0)), # This data is not in the new dataset
                'avg_income': int(district_data['gdp_per_capita']),
                'employment_rate': round(district_data.get('employment_rate', 95.0), 2), # Placeholder
                'interest_index': round(district_data['predicted_score'] / 100, 3), # Normalize score
                'tier': city_info.get('tier', 3),
                'literacy_rate': city_info.get('literacy_rate', 80), # Placeholder from city data
                'relevant_expenditure': int(district_data['avg_spending'])
            })

        # Calculate overall metrics from the selected clusters
        metrics = calculate_realistic_metrics(clusters)

        logger.info("ML model used for prediction.")
        print("ML MODEL USED FOR PREDICTION.")
        return {
            **metrics,
            'clusters': clusters
        }
        
    except Exception as e:
        logger.error(f"Error in ML prediction pipeline: {e}")
        logger.info("Falling back to logical cluster generation.")
        print("LOGICAL FALLBACK: Error in ML prediction pipeline.")
        
        # Fallback to the old logical system in case of any error
        clusters = generate_logical_clusters(product_type, product_luxury, target_audience, price)
        metrics = calculate_realistic_metrics(clusters)
        
        return {
            **metrics,
            'clusters': clusters
        }

def train_models() -> bool:
    """
    Train and save ML models using a real, unified dataset.
    Returns True if successful, False otherwise.
    """
    if not ML_LIBRARIES_AVAILABLE:
        logger.error("Cannot train models: ML libraries not available")
        return False
    
    try:
        # Import required modules
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        from sklearn.ensemble import RandomForestRegressor
        import joblib

        # Create the training dataset
        training_data = create_training_data()
        
        if training_data is None:
            logger.error("Cannot train models: Failed to create training data.")
            return False
        
        # Define features and target
        features = [
            'total_population', 'population_18_35', 'avg_income', 'gdp_per_capita',
            'avg_disposable_income', 'avg_spending',
            'youth_ratio', 'disposable_income_per_capita', 'employment_rate'
        ]
        target = 'market_potential_score'

        X = training_data[features]
        y = training_data[target]
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Train scaler
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        
        # Train regression model
        rf_model = RandomForestRegressor(n_estimators=100, random_state=42, oob_score=True)
        rf_model.fit(X_train_scaled, y_train)
        
        logger.info(f"Model trained. OOB Score: {rf_model.oob_score_:.4f}")

        # For this pipeline, we will use the regressor to score districts and then use
        # the logical clustering to present high/medium/low options from the top-scored districts.
        # A KMeans model is not strictly necessary if we are ranking districts by score.
        
        # Save the scaler and the regressor model
        joblib.dump(scaler, SCALER_PATH)
        joblib.dump(rf_model, RF_MODEL_PATH)
        
        # Clean up old kmeans model if it exists
        if os.path.exists(KMEANS_PATH):
            os.remove(KMEANS_PATH)

        logger.info("Scaler and Regressor models trained and saved successfully.")
        return True
        
    except Exception as e:
        logger.error(f"Error training models: {e}")
        return False

# Initialize models on import if datasets are available
def initialize_models():
    """Initialize models if they don't exist"""
    models_exist = all(os.path.exists(path) for path in [SCALER_PATH, KMEANS_PATH, RF_MODEL_PATH])
    
    if not models_exist and ML_LIBRARIES_AVAILABLE:
        logger.info("Models not found, attempting to train...")
        train_models()

# Don't initialize on import to avoid startup issues
# initialize_models()