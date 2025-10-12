import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json
import os

# Define the base directory for datasets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')

# --- 2. Load Datasets ---
# Demographics
population = pd.read_csv(os.path.join(DATASETS_DIR, 'Population_of_India.csv'))
district_population = pd.read_csv(os.path.join(DATASETS_DIR, 'India_Districts_Population.csv'))

# Income & Expenditure
personal_finance = pd.read_csv(os.path.join(DATASETS_DIR, 'Indian_Personal_Finance.csv'))
income_exp = pd.read_csv(os.path.join(DATASETS_DIR, 'Income_Expenditure.csv'))

# Employment
unemployment = pd.read_csv(os.path.join(DATASETS_DIR, 'Unemployment_India.csv'))
employment_data = pd.read_csv(os.path.join(DATASETS_DIR, 'Employment_India.csv'))

# Optional Interest / Spending
customer_spend = pd.read_csv(os.path.join(DATASETS_DIR, 'Customer_Spend.csv'))

# --- 3. Data Cleaning & Preprocessing (Simplified for example) ---
# This section would contain the actual data cleaning and merging logic
# from the notebook. For now, we'll assume a merged_data DataFrame exists.

# Placeholder for merged and preprocessed data
# In a real scenario, this would involve extensive merging and feature engineering
# based on the loaded datasets.
merged_data = pd.DataFrame({
    'income': np.random.rand(100) * 100000,
    'population_density': np.random.rand(100) * 1000,
    'avg_spend': np.random.rand(100) * 50000,
    'interest_score': np.random.rand(100) * 10,
    'price': np.random.rand(100) * 1000,
    'adoption_rate': np.random.rand(100) * 100,
    'latitude': np.random.rand(100) * 10 + 20, # Sample Indian latitudes
    'longitude': np.random.rand(100) * 10 + 70 # Sample Indian longitudes
})

# Scaling
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(merged_data[['income', 'population_density', 'avg_spend', 'interest_score', 'price']])

# KMeans Clustering
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10) # n_init added for KMeans warning
clusters = kmeans.fit_predict(X_scaled)
merged_data['cluster'] = clusters

# RandomForest Regressor
X_ml = merged_data[['income', 'population_density', 'avg_spend', 'interest_score', 'price', 'cluster']]
y_ml = merged_data['adoption_rate']

model = RandomForestRegressor(random_state=42)
model.fit(X_ml, y_ml)

# --- ML Pipeline Function ---
def run_prediction_pipeline(product_type, product_luxury, target_audience, price, region):
    # This function will simulate the ML prediction based on input parameters.
    # In a real scenario, this would involve:
    # 1. Mapping input parameters to features used by the ML model.
    # 2. Fetching relevant demographic/geographic data for the 'region'.
    # 3. Preprocessing this data.
    # 4. Running the KMeans model to get cluster labels.
    # 5. Running the RandomForestRegressor to predict reach and success probability.

    # Placeholder for actual ML logic
    # For now, we return dummy data based on the input.

    # Simulate some logic based on input
    predicted_reach = 50.0 + (price * 0.1) - (len(product_type) * 0.5)
    success_probability = 0.75 - (price * 0.001)
    
    # Ensure values are within reasonable bounds
    predicted_reach = max(0.0, min(100.0, predicted_reach))
    success_probability = max(0.0, min(1.0, success_probability))

    # Dummy clusters (replace with actual KMeans output for the region)
    dummy_clusters = [
        {'lat': 28.7041, 'lon': 77.1025, 'label': 'High', 'population_density': 10000, 'avg_income': 80000, 'employment_rate': 0.85, 'interest_index': 0.9},
        {'lat': 19.0760, 'lon': 72.8777, 'label': 'Medium', 'population_density': 8000, 'avg_income': 60000, 'employment_rate': 0.75, 'interest_index': 0.7},
        {'lat': 13.0827, 'lon': 80.2707, 'label': 'Low', 'population_density': 5000, 'avg_income': 40000, 'employment_rate': 0.60, 'interest_index': 0.5},
    ]

    return {
        'predicted_reach': predicted_reach,
        'success_probability': success_probability,
        'clusters': dummy_clusters,
        'model_confidence': 0.85 # Placeholder
    }
