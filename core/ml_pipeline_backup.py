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

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json
import os
import re # Import regex for cleaning data
import joblib # Import joblib for model persistence

# Define the base directory for datasets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
ML_MODELS_DIR = os.path.join(BASE_DIR, 'core', 'models_ml')

# Ensure the ML models directory exists
os.makedirs(ML_MODELS_DIR, exist_ok=True)

# File paths for saved models
SCALER_PATH = os.path.join(ML_MODELS_DIR, 'scaler.joblib')
KMEANS_PATH = os.path.join(ML_MODELS_DIR, 'kmeans_model.joblib')
RF_MODEL_PATH = os.path.join(ML_MODELS_DIR, 'random_forest_model.joblib')

# Function to clean column names
def clean_col_names(df):
    df.columns = df.columns.str.strip()
    return df

# --- 2. Load Datasets ---
# Demographics
population_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Population_of_India.csv')))
district_population_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'India_Districts_Population.csv')))

# Income & Expenditure
personal_finance_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Indian_Personal_Finance.csv')))
income_expenditure_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Income_Expenditure.csv')))

# Employment
unemployment_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Unemployment_India.csv')))
employment_data_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Employment_India.csv')))

# Optional Interest / Spending
customer_spend_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Customer_Spend.csv')))

# --- 3. Data Cleaning & Preprocessing ---

# 3.1. Clean Population_of_India.csv
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

import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
import json
import os
import re # Import regex for cleaning data
import joblib # Import joblib for model persistence

# Define the base directory for datasets
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASETS_DIR = os.path.join(BASE_DIR, 'datasets')
ML_MODELS_DIR = os.path.join(BASE_DIR, 'core', 'models_ml')

# Ensure the ML models directory exists
os.makedirs(ML_MODELS_DIR, exist_ok=True)

# File paths for saved models
SCALER_PATH = os.path.join(ML_MODELS_DIR, 'scaler.joblib')
KMEANS_PATH = os.path.join(ML_MODELS_DIR, 'kmeans_model.joblib')
RF_MODEL_PATH = os.path.join(ML_MODELS_DIR, 'random_forest_model.joblib')

# Function to clean column names
def clean_col_names(df):
    df.columns = df.columns.str.strip()
    return df

# --- 2. Load Datasets ---
# Demographics
population_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Population_of_India.csv')))
district_population_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'India_Districts_Population.csv')))

# Income & Expenditure
personal_finance_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Indian_Personal_Finance.csv')))
income_expenditure_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Income_Expenditure.csv')))

# Employment
unemployment_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Unemployment_India.csv')))
employment_data_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Employment_India.csv')))

# Optional Interest / Spending
customer_spend_india = clean_col_names(pd.read_csv(os.path.join(DATASETS_DIR, 'Customer_Spend.csv')))

# --- 3. Data Cleaning & Preprocessing ---
# Note: merged_data is defined later in the file. This section will be moved to after the merge.

# Aggregate customer spending by category (national average)
avg_spend_by_category = customer_spend_india.groupby('Category')['Amount'].mean()
for category, amount in avg_spend_by_category.items():
    merged_data[f'National_Avg_Spend_{category.replace(" ", "_")}'] = amount

# Aggregate personal finance by education and occupation (national average)
avg_income_by_education = personal_finance_india.groupby('Education')['Income'].mean()
for education, income in avg_income_by_education.items():
    merged_data[f'National_Avg_Income_Edu_{education.replace(" ", "_")}'] = income

avg_disposable_income_by_occupation = personal_finance_india.groupby('Occupation')['Disposable_Income'].mean()
for occupation, disposable_income in avg_disposable_income_by_occupation.items():
    merged_data[f'National_Avg_Disposable_Income_Occ_{occupation.replace(" ", "_")}'] = disposable_income

# Aggregate employment data by education level and job title (national average)
avg_salary_by_education_level = employment_data_india.groupby('Education Level')['Monthly Salary (INR)'].mean()
for edu_level, salary in avg_salary_by_education_level.items():
    merged_data[f'National_Avg_Salary_Edu_{edu_level.replace(" ", "_")}'] = salary

avg_salary_by_job_title = employment_data_india.groupby('Job Title')['Monthly Salary (INR)'].mean()
for job_title, salary in avg_salary_by_job_title.items():
    merged_data[f'National_Avg_Salary_Job_{job_title.replace(" ", "_")}'] = salary

# --- 5. Feature Engineering ---
# For now, the merged data itself forms the features.
# More complex feature engineering can be added here later.

# Define target variable (adoption_rate - this is still hypothetical/dummy for now)
# In a real scenario, 'adoption_rate' would come from a dataset or be derived.
# For now, let's create a dummy 'adoption_rate' based on some features for training purposes
merged_data['adoption_rate'] = (
    (merged_data['Population'] / 1000000) * 0.5 +
    (merged_data['Density (per km2)'] / 100) * 0.2 +
    (merged_data['Avg_District_Literacy'] / 100) * 0.3 -
    (merged_data['Estimated Unemployment Rate (%)'] / 100) * 0.4 +
    (merged_data['National_Avg_Personal_Income'] / 100000) * 0.1
).clip(lower=0, upper=100) # Ensure adoption rate is between 0 and 100

# --- 6. Model Training ---

# Features for scaling and ML
features_for_scaling = [
    'Population', 'Area (km2)', 'Density (per km2)',
    'Avg_District_Population', 'Avg_District_Growth', 'Avg_District_Literacy',
    'Estimated Unemployment Rate (%)', 'Estimated Employed', 'Estimated Labour Participation Rate (%)',
    'latitude', 'longitude',
    'National_Avg_Personal_Income', 'National_Avg_Disposable_Income', 'National_Avg_Customer_Spend', 'National_Avg_Employment_Salary',
    'National_Avg_Household_Spending', 'National_Avg_GDP'
]

# Add dynamically generated average spend, income, and salary features
for col in merged_data.columns:
    if col.startswith('National_Avg_Spend_') or \
       col.startswith('National_Avg_Income_Edu_') or \
       col.startswith('National_Avg_Disposable_Income_Occ_') or \
       col.startswith('National_Avg_Salary_Edu_') or \
       col.startswith('National_Avg_Salary_Job_'):
        features_for_scaling.append(col)

# Drop rows with NaN in features_for_scaling if any remain
merged_data.dropna(subset=features_for_scaling, inplace=True)

# Check if models exist, otherwise train and save them
if os.path.exists(SCALER_PATH) and os.path.exists(KMEANS_PATH) and os.path.exists(RF_MODEL_PATH):
    scaler = joblib.load(SCALER_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    model = joblib.load(RF_MODEL_PATH)
else:
    # Scaling
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(merged_data[features_for_scaling])
    joblib.dump(scaler, SCALER_PATH)

    # KMeans Clustering
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    merged_data['cluster'] = clusters
    joblib.dump(kmeans, KMEANS_PATH)

    # RandomForest Regressor
    X_ml = merged_data[features_for_scaling + ['cluster']]
    y_ml = merged_data['adoption_rate']

    # Add dummy categorical features for OneHotEncoder fitting
    # These will be replaced by actual input in run_prediction_pipeline
    merged_data['product_type'] = 'Electronics' # Placeholder
    merged_data['product_luxury'] = 'Mid-range' # Placeholder
    merged_data['target_audience'] = 'Adults' # Placeholder
    merged_data['price'] = 1000 # Placeholder

    categorical_features = ['product_type', 'product_luxury', 'target_audience']
    onehot_encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    encoded_features = onehot_encoder.fit_transform(merged_data[categorical_features])
    encoded_feature_names = onehot_encoder.get_feature_names_out(categorical_features)
    encoded_df = pd.DataFrame(encoded_features, columns=encoded_feature_names, index=merged_data.index)
    merged_data = pd.concat([merged_data, encoded_df], axis=1)

    # Update features_for_scaling to include new categorical features and price
    features_for_scaling.extend(encoded_feature_names)
    features_for_scaling.append('price')

    # Ensure all features in features_for_scaling are present in merged_data and handle NaNs
    for feature in features_for_scaling:
        if feature not in merged_data.columns:
            merged_data[feature] = 0 # Add missing feature columns with default 0
    merged_data.dropna(subset=features_for_scaling, inplace=True)

    X_ml = merged_data[features_for_scaling + ['cluster']]
    y_ml = merged_data['adoption_rate']

    model = RandomForestRegressor(random_state=42)
    model.fit(X_ml, y_ml)
    joblib.dump(model, RF_MODEL_PATH)
    joblib.dump(onehot_encoder, os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib'))

    # --- ML Pipeline Function ---

    def run_prediction_pipeline(product_type, product_luxury, target_audience, price, region):

        # Ensure models are loaded (they are loaded globally if they exist)

        global scaler, kmeans, model, merged_data, features_for_scaling, onehot_encoder

        if 'scaler' not in globals() or 'kmeans' not in globals() or 'model' not in globals() or 'onehot_encoder' not in globals():

            if os.path.exists(SCALER_PATH) and os.path.exists(KMEANS_PATH) and os.path.exists(RF_MODEL_PATH) and os.path.exists(os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib')):

                scaler = joblib.load(SCALER_PATH)

                kmeans = joblib.load(KMEANS_PATH)

                model = joblib.load(RF_MODEL_PATH)

                onehot_encoder = joblib.load(os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib'))

            else:

                raise Exception("ML models not found. Please ensure models are trained and saved.")

    

        # Prepare input features for prediction

        # 1. Get state-level features for the given region

        region_data_row = merged_data[merged_data['State'].str.contains(region, case=False, na=False)]

    

        if region_data_row.empty:

            return {

                'predicted_reach': 0.0,

                'success_probability': 0.0,

                'clusters': [],

                'model_confidence': 0.0,

                'message': f"Region '{region}' not found in demographic data."

            }

    

        # Take the first matching region if multiple exist

        input_features_base = region_data_row.iloc[0][features_for_scaling].to_dict()

    

        # Create input DataFrame for prediction
        input_df_pred = pd.DataFrame([input_features_base])

        # Add price
        input_df_pred['price'] = price

        # Create a DataFrame for categorical inputs
        categorical_input_df = pd.DataFrame([[product_type, product_luxury, target_audience]],
                                            columns=['product_type', 'product_luxury', 'target_audience'])

        # One-hot encode the categorical inputs
        encoded_categorical_features = onehot_encoder.transform(categorical_input_df)
        encoded_categorical_df = pd.DataFrame(encoded_categorical_features, columns=onehot_encoder.get_feature_names_out(categorical_input_df.columns))

        # Concatenate one-hot encoded features
        input_df_pred = pd.concat([input_df_pred, encoded_categorical_df], axis=1)

        # Ensure all features in features_for_scaling are present in input_df_pred
        # and fill missing ones with 0 (important for one-hot encoded columns that might not appear in input)
        for feature in features_for_scaling:
            if feature not in input_df_pred.columns:
                input_df_pred[feature] = 0

        # Reorder columns to match the order used during training
        input_df_pred = input_df_pred[features_for_scaling]

        # Prepare the numerical features for scaling
        input_for_scaling = input_df_pred.values

        # Scale the input features
        input_scaled = scaler.transform(input_for_scaling)

        # Predict the cluster for the input
        input_cluster = kmeans.predict(input_scaled)[0]

        # Prepare input for RandomForestRegressor
        # This needs to match X_ml used during training (features_for_scaling + ['cluster'])
        input_for_rf = np.append(input_scaled[0], input_cluster).reshape(1, -1)

        # Make prediction
        predicted_reach = model.predict(input_for_rf)[0]

    

        # Ensure values are within reasonable bounds

        predicted_reach = max(0.0, min(100.0, predicted_reach))

        success_probability = predicted_reach / 100.0 # Simple conversion

    

        # Generate clusters for visualization (using the predicted cluster's characteristics)

        cluster_centroid = kmeans.cluster_centers_[input_cluster]

        original_features_approx = scaler.inverse_transform(cluster_centroid.reshape(1, -1))[0]

    

        # Find a representative latitude and longitude for the predicted region/state

        # This assumes 'latitude' and 'longitude' columns are added to merged_data during preprocessing

        # For now, I'll use a fixed lat/lon for the region if available, otherwise a default.

        # This is a gap in the current merged_data, which doesn't have lat/lon for states.

        # I will add a placeholder for lat/lon in merged_data during the initial processing.

        # For now, let's use the lat/lon from the first entry of the region_data if available

        if 'latitude' in region_data_row.columns and 'longitude' in region_data_row.columns and not region_data_row.empty:

            cluster_lat = region_data_row['latitude'].iloc[0]

            cluster_lon = region_data_row['longitude'].iloc[0]

        else:

            # Default to approximate center of India if lat/lon not available in merged_data

            cluster_lat = 20.5937

            cluster_lon = 78.9629

    

        predicted_cluster_info = {

            'lat': cluster_lat,

            'lon': cluster_lon,

            'label': f"Cluster {input_cluster}",

            'population_density': original_features_approx[features_for_scaling.index('Density (per km2)')] if 'Density (per km2)' in features_for_scaling else 0,

            'avg_income': original_features_approx[features_for_scaling.index('Overall_Avg_Income')] if 'Overall_Avg_Income' in features_for_scaling else 0,

            'employment_rate': original_features_approx[features_for_scaling.index('Estimated Unemployment Rate (%)')] if 'Estimated Unemployment Rate (%)' in features_for_scaling else 0,

            'interest_index': 0.75 # Placeholder for now

        }

    

        return {

            'predicted_reach': predicted_reach,

            'success_probability': success_probability,

            'clusters': [predicted_cluster_info],

            'model_confidence': 0.85 # Still a placeholder

        }


# Aggregate customer spending by category (national average)
avg_spend_by_category = customer_spend_india.groupby('Category')['Amount'].mean()
for category, amount in avg_spend_by_category.items():
    merged_data[f'National_Avg_Spend_{category.replace(" ", "_")}'] = amount

# Aggregate personal finance by education and occupation (national average)
avg_income_by_education = personal_finance_india.groupby('Education')['Income'].mean()
for education, income in avg_income_by_education.items():
    merged_data[f'National_Avg_Income_Edu_{education.replace(" ", "_")}'] = income

avg_disposable_income_by_occupation = personal_finance_india.groupby('Occupation')['Disposable_Income'].mean()
for occupation, disposable_income in avg_disposable_income_by_occupation.items():
    merged_data[f'National_Avg_Disposable_Income_Occ_{occupation.replace(" ", "_")}'] = disposable_income

# Aggregate employment data by education level and job title (national average)
avg_salary_by_education_level = employment_data_india.groupby('Education Level')['Monthly Salary (INR)'].mean()
for edu_level, salary in avg_salary_by_education_level.items():
    merged_data[f'National_Avg_Salary_Edu_{edu_level.replace(" ", "_")}'] = salary

avg_salary_by_job_title = employment_data_india.groupby('Job Title')['Monthly Salary (INR)'].mean()
for job_title, salary in avg_salary_by_job_title.items():
    merged_data[f'National_Avg_Salary_Job_{job_title.replace(" ", "_")}'] = salary

# --- 5. Feature Engineering ---
# For now, the merged data itself forms the features.
# More complex feature engineering can be added here later.

# Define target variable (adoption_rate - this is still hypothetical/dummy for now)
# In a real scenario, 'adoption_rate' would come from a dataset or be derived.
# For now, let's create a dummy 'adoption_rate' based on some features for training purposes
merged_data['adoption_rate'] = (
    (merged_data['Population'] / 1000000) * 0.5 +
    (merged_data['Density (per km2)'] / 100) * 0.2 +
    (merged_data['Avg_District_Literacy'] / 100) * 0.3 -
    (merged_data['Estimated Unemployment Rate (%)'] / 100) * 0.4 +
    (merged_data['National_Avg_Personal_Income'] / 100000) * 0.1
).clip(lower=0, upper=100) # Ensure adoption rate is between 0 and 100

# --- 6. Model Training ---

# Features for scaling and ML
features_for_scaling = [
    'Population', 'Area (km2)', 'Density (per km2)',
    'Avg_District_Population', 'Avg_District_Growth', 'Avg_District_Literacy',
    'Estimated Unemployment Rate (%)', 'Estimated Employed', 'Estimated Labour Participation Rate (%)',
    'latitude', 'longitude',
    'Avg_Monthly_Income', 'Avg_Monthly_Expenditure',
    'National_Avg_Personal_Income', 'National_Avg_Disposable_Income', 'National_Avg_Customer_Spend', 'National_Avg_Employment_Salary'
]

# Add dynamically generated average spend, income, and salary features
for col in merged_data.columns:
    if col.startswith('National_Avg_Spend_') or \
       col.startswith('National_Avg_Income_Edu_') or \
       col.startswith('National_Avg_Disposable_Income_Occ_') or \
       col.startswith('National_Avg_Salary_Edu_') or \
       col.startswith('National_Avg_Salary_Job_'):
        features_for_scaling.append(col)

# Drop rows with NaN in features_for_scaling if any remain
merged_data.dropna(subset=features_for_scaling, inplace=True)

# Check if models exist, otherwise train and save them
if os.path.exists(SCALER_PATH) and os.path.exists(KMEANS_PATH) and os.path.exists(RF_MODEL_PATH):
    scaler = joblib.load(SCALER_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    model = joblib.load(RF_MODEL_PATH)
else:
    # Scaling
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(merged_data[features_for_scaling])
    joblib.dump(scaler, SCALER_PATH)

    # KMeans Clustering
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    merged_data['cluster'] = clusters
    joblib.dump(kmeans, KMEANS_PATH)

    # RandomForest Regressor
    X_ml = merged_data[features_for_scaling + ['cluster']]
    y_ml = merged_data['adoption_rate']

    # Add dummy categorical features for OneHotEncoder fitting
    # These will be replaced by actual input in run_prediction_pipeline
    merged_data['product_type'] = 'Electronics' # Placeholder
    merged_data['product_luxury'] = 'Mid-range' # Placeholder
    merged_data['target_audience'] = 'Adults' # Placeholder
    merged_data['price'] = 1000 # Placeholder

    categorical_features = ['product_type', 'product_luxury', 'target_audience']
    onehot_encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    encoded_features = onehot_encoder.fit_transform(merged_data[categorical_features])
    encoded_feature_names = onehot_encoder.get_feature_names_out(categorical_features)
    encoded_df = pd.DataFrame(encoded_features, columns=encoded_feature_names, index=merged_data.index)
    merged_data = pd.concat([merged_data, encoded_df], axis=1)

    # Update features_for_scaling to include new categorical features and price
    features_for_scaling.extend(encoded_feature_names)
    features_for_scaling.append('price')

    # Ensure all features in features_for_scaling are present in merged_data and handle NaNs
    for feature in features_for_scaling:
        if feature not in merged_data.columns:
            merged_data[feature] = 0 # Add missing feature columns with default 0
    merged_data.dropna(subset=features_for_scaling, inplace=True)

    X_ml = merged_data[features_for_scaling + ['cluster']]
    y_ml = merged_data['adoption_rate']

    model = RandomForestRegressor(random_state=42)
    model.fit(X_ml, y_ml)
    joblib.dump(model, RF_MODEL_PATH)
    joblib.dump(onehot_encoder, os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib'))

    # --- ML Pipeline Function ---

    def run_prediction_pipeline(product_type, product_luxury, target_audience, price, region):

        # Ensure models are loaded (they are loaded globally if they exist)

        global scaler, kmeans, model, merged_data, features_for_scaling, onehot_encoder

        if 'scaler' not in globals() or 'kmeans' not in globals() or 'model' not in globals() or 'onehot_encoder' not in globals():

            if os.path.exists(SCALER_PATH) and os.path.exists(KMEANS_PATH) and os.path.exists(RF_MODEL_PATH) and os.path.exists(os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib')):

                scaler = joblib.load(SCALER_PATH)

                kmeans = joblib.load(KMEANS_PATH)

                model = joblib.load(RF_MODEL_PATH)

                onehot_encoder = joblib.load(os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib'))

            else:

                raise Exception("ML models not found. Please ensure models are trained and saved.")

    

        # Prepare input features for prediction

        # 1. Get state-level features for the given region

        region_data_row = merged_data[merged_data['State'].str.contains(region, case=False, na=False)]

    

        if region_data_row.empty:

            return {

                'predicted_reach': 0.0,

                'success_probability': 0.0,

                'clusters': [],

                'model_confidence': 0.0,

                'message': f"Region '{region}' not found in demographic data."

            }

    

        # Take the first matching region if multiple exist

        input_features_base = region_data_row.iloc[0][features_for_scaling].to_dict()

    

        # Create input DataFrame for prediction
        input_df_pred = pd.DataFrame([input_features_base])

        # Add price
        input_df_pred['price'] = price

        # Create a DataFrame for categorical inputs
        categorical_input_df = pd.DataFrame([[product_type, product_luxury, target_audience]],
                                            columns=['product_type', 'product_luxury', 'target_audience'])

        # One-hot encode the categorical inputs
        encoded_categorical_features = onehot_encoder.transform(categorical_input_df)
        encoded_categorical_df = pd.DataFrame(encoded_categorical_features, columns=onehot_encoder.get_feature_names_out(categorical_input_df.columns))

        # Concatenate one-hot encoded features
        input_df_pred = pd.concat([input_df_pred, encoded_categorical_df], axis=1)

        # Ensure all features in features_for_scaling are present in input_df_pred
        # and fill missing ones with 0 (important for one-hot encoded columns that might not appear in input)
        for feature in features_for_scaling:
            if feature not in input_df_pred.columns:
                input_df_pred[feature] = 0

        # Reorder columns to match the order used during training
        input_df_pred = input_df_pred[features_for_scaling]

        # Prepare the numerical features for scaling
        input_for_scaling = input_df_pred.values

        # Scale the input features
        input_scaled = scaler.transform(input_for_scaling)

        # Predict the cluster for the input
        input_cluster = kmeans.predict(input_scaled)[0]

        # Prepare input for RandomForestRegressor
        # This needs to match X_ml used during training (features_for_scaling + ['cluster'])
        input_for_rf = np.append(input_scaled[0], input_cluster).reshape(1, -1)

        # Make prediction
        predicted_reach = model.predict(input_for_rf)[0]

    

        # Ensure values are within reasonable bounds

        predicted_reach = max(0.0, min(100.0, predicted_reach))

        success_probability = predicted_reach / 100.0 # Simple conversion

    

        # Generate clusters for visualization (using the predicted cluster's characteristics)

        cluster_centroid = kmeans.cluster_centers_[input_cluster]

        original_features_approx = scaler.inverse_transform(cluster_centroid.reshape(1, -1))[0]

    

        # Find a representative latitude and longitude for the predicted region/state

        # This assumes 'latitude' and 'longitude' columns are added to merged_data during preprocessing

        # For now, I'll use a fixed lat/lon for the region if available, otherwise a default.

        # This is a gap in the current merged_data, which doesn't have lat/lon for states.

        # I will add a placeholder for lat/lon in merged_data during the initial processing.

        # For now, let's use the lat/lon from the first entry of the region_data if available

        if 'latitude' in region_data_row.columns and 'longitude' in region_data_row.columns and not region_data_row.empty:

            cluster_lat = region_data_row['latitude'].iloc[0]

            cluster_lon = region_data_row['longitude'].iloc[0]

        else:

            # Default to approximate center of India if lat/lon not available in merged_data

            cluster_lat = 20.5937

            cluster_lon = 78.9629

    

        predicted_cluster_info = {

            'lat': cluster_lat,

            'lon': cluster_lon,

            'label': f"Cluster {input_cluster}",

            'population_density': original_features_approx[features_for_scaling.index('Density (per km2)')] if 'Density (per km2)' in features_for_scaling else 0,

            'avg_income': original_features_approx[features_for_scaling.index('National_Avg_Personal_Income')] if 'National_Avg_Personal_Income' in features_for_scaling else 0,

            'employment_rate': original_features_approx[features_for_scaling.index('Estimated Unemployment Rate (%)')] if 'Estimated Unemployment Rate (%)' in features_for_scaling else 0,

            'interest_index': 0.75 # Placeholder for now

        }

    

        return {

            'predicted_reach': predicted_reach,

            'success_probability': success_probability,

            'clusters': [predicted_cluster_info],

            'model_confidence': 0.85 # Still a placeholder

        }



# 3.2. Clean India_Districts_Population.csv
district_population_india.rename(columns={'State': 'State', 'District': 'District'}, inplace=True)
# Clean 'Population' column
district_population_india['Population'] = district_population_india['Population'].astype(str).str.replace(',', '', regex=False)
district_population_india['Population'] = pd.to_numeric(district_population_india['Population'], errors='coerce').fillna(0).astype(int)
# Clean 'Growth' column
district_population_india['Growth'] = district_population_india['Growth'].astype(str).str.replace('%', '', regex=False).str.strip()
district_population_india['Growth'] = pd.to_numeric(district_population_india['Growth'], errors='coerce').fillna(0.0)
# Clean 'Literacy' column
district_population_india['Literacy'] = district_population_india['Literacy'].astype(str).str.replace('%', '', regex=False).str.strip()
district_population_india['Literacy'] = pd.to_numeric(district_population_india['Literacy'], errors='coerce').fillna(0.0)

# Aggregate district data to state level
state_district_agg = district_population_india.groupby('State').agg(
    Avg_District_Population=('Population', 'mean'),
    Avg_District_Growth=('Growth', 'mean'),
    Avg_District_Literacy=('Literacy', 'mean')
).reset_index()

# 3.3. Clean Unemployment_India.csv
unemployment_india.rename(columns={'Region': 'State'}, inplace=True)
unemployment_india['Date'] = pd.to_datetime(unemployment_india['Date'], dayfirst=True)
# Take the latest available data for each state
unemployment_latest = unemployment_india.loc[unemployment_india.groupby('State')['Date'].idxmax()]
unemployment_cleaned = unemployment_latest[['State', 'Estimated Unemployment Rate (%)', 'Estimated Employed', 'Estimated Labour Participation Rate (%)']]

# 3.4. Clean Indian_Personal_Finance.csv
# No direct state mapping, aggregate overall or by City_Tier
personal_finance_india['Income'] = pd.to_numeric(personal_finance_india['Income'], errors='coerce').fillna(0)
personal_finance_india['Disposable_Income'] = pd.to_numeric(personal_finance_india['Disposable_Income'], errors='coerce').fillna(0)
avg_income_by_city_tier = personal_finance_india.groupby('City_Tier').agg(
    Avg_Income=('Income', 'mean'),
    Avg_Disposable_Income=('Disposable_Income', 'mean')
).reset_index()

# 3.5. Clean Employment_India.csv
# No direct state mapping, aggregate overall or by Location
employment_data_india['Monthly Salary (INR)'] = pd.to_numeric(employment_data_india['Monthly Salary (INR)'], errors='coerce').fillna(0)
avg_salary_by_location = employment_data_india.groupby('Location').agg(
    Avg_Monthly_Salary=('Monthly Salary (INR)', 'mean')
).reset_index()

# --- 4. Merging Datasets ---

# Start with population data
merged_data = population_india_cleaned

# Placeholder for State Lat/Lon (approximate centroids)
state_lat_lon = {
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
    'Punjab': (30.7333, 76.7794),
    'Rajasthan': (27.0238, 74.2179),
    'Sikkim': (27.5330, 88.5122),
    'Tamil Nadu': (11.1271, 78.6569),
    'Telangana': (18.1124, 79.0193),
    'Tripura': (23.9408, 91.9882),
    'Uttar Pradesh': (26.8467, 80.9462),
    'Uttarakhand': (30.0668, 79.0193),
    'West Bengal': (22.9868, 87.8550),
    'Andaman and Nicobar Islands': (11.7401, 92.6586),
    'Chandigarh': (30.7333, 76.7794),
    'Dadra and Nagar Haveli and Daman and Diu': (20.1809, 73.0169),
    'Delhi': (28.7041, 77.1025),
    'Jammu and Kashmir': (33.7782, 76.5762),
    'Ladakh': (34.1526, 77.5800),
    'Lakshadweep': (10.5667, 72.6417),
    'Puducherry': (11.9416, 79.8083)
}

merged_data['latitude'] = merged_data['State'].map(lambda x: state_lat_lon.get(x, (20.5937, 78.9629))[0]) # Default to India center
merged_data['longitude'] = merged_data['State'].map(lambda x: state_lat_lon.get(x, (20.5937, 78.9629))[1]) # Default to India center

# Merge with aggregated district data
merged_data = pd.merge(merged_data, state_district_agg, on='State', how='left')

# Merge with unemployment data
merged_data = pd.merge(merged_data, unemployment_cleaned, on='State', how='left')

# Fill any remaining NaN values after merges (e.g., states not in all datasets)
merged_data.fillna(0, inplace=True) # Simple fill for now, more sophisticated imputation can be added

# 3.6. Clean Income_Expenditure.csv
income_expenditure_india.rename(columns={'States': 'State'}, inplace=True)
income_expenditure_india['Avg_Monthly_Income'] = pd.to_numeric(income_expenditure_india['Average Monthly Income (INR)'], errors='coerce').fillna(0)
income_expenditure_india['Avg_Monthly_Expenditure'] = pd.to_numeric(income_expenditure_india['Average Monthly Expenditure (INR)'], errors='coerce').fillna(0)
income_expenditure_cleaned = income_expenditure_india[['State', 'Avg_Monthly_Income', 'Avg_Monthly_Expenditure']]

# Merge with income and expenditure data
merged_data = pd.merge(merged_data, income_expenditure_cleaned, on='State', how='left')

# Add overall economic indicators (national averages, as state-level mapping is not direct for all datasets)
merged_data['National_Avg_Personal_Income'] = personal_finance_india['Income'].mean()
merged_data['National_Avg_Disposable_Income'] = personal_finance_india['Disposable_Income'].mean()
merged_data['National_Avg_Customer_Spend'] = customer_spend_india['Amount'].mean()
merged_data['National_Avg_Employment_Salary'] = employment_data_india['Monthly Salary (INR)'].mean()

# Aggregate customer spending by category (national average)
avg_spend_by_category = customer_spend_india.groupby('Category')['Amount'].mean()
for category, amount in avg_spend_by_category.items():
    merged_data[f'National_Avg_Spend_{category.replace(" ", "_")}'] = amount

# Aggregate personal finance by education and occupation (national average)
avg_income_by_education = personal_finance_india.groupby('Education')['Income'].mean()
for education, income in avg_income_by_education.items():
    merged_data[f'National_Avg_Income_Edu_{education.replace(" ", "_")}'] = income

avg_disposable_income_by_occupation = personal_finance_india.groupby('Occupation')['Disposable_Income'].mean()
for occupation, disposable_income in avg_disposable_income_by_occupation.items():
    merged_data[f'National_Avg_Disposable_Income_Occ_{occupation.replace(" ", "_")}'] = disposable_income

# Aggregate employment data by education level and job title (national average)
avg_salary_by_education_level = employment_data_india.groupby('Education Level')['Monthly Salary (INR)'].mean()
for edu_level, salary in avg_salary_by_education_level.items():
    merged_data[f'National_Avg_Salary_Edu_{edu_level.replace(" ", "_")}'] = salary

avg_salary_by_job_title = employment_data_india.groupby('Job Title')['Monthly Salary (INR)'].mean()
for job_title, salary in avg_salary_by_job_title.items():
    merged_data[f'National_Avg_Salary_Job_{job_title.replace(" ", "_")}'] = salary

# --- 5. Feature Engineering ---
# For now, the merged data itself forms the features.
# More complex feature engineering can be added here later.

# Define target variable (adoption_rate - this is still hypothetical/dummy for now)
# In a real scenario, 'adoption_rate' would come from a dataset or be derived.
# For now, let's create a dummy 'adoption_rate' based on some features for training purposes
merged_data['adoption_rate'] = (
    (merged_data['Population'] / 1000000) * 0.5 +
    (merged_data['Density (per km2)'] / 100) * 0.2 +
    (merged_data['Avg_District_Literacy'] / 100) * 0.3 -
    (merged_data['Estimated Unemployment Rate (%)'] / 100) * 0.4 +
    (merged_data['National_Avg_Personal_Income'] / 100000) * 0.1
).clip(lower=0, upper=100) # Ensure adoption rate is between 0 and 100

# --- 6. Model Training ---

# Features for scaling and ML
features_for_scaling = [
    'Population', 'Area (km2)', 'Density (per km2)',
    'Avg_District_Population', 'Avg_District_Growth', 'Avg_District_Literacy',
    'Estimated Unemployment Rate (%)', 'Estimated Employed', 'Estimated Labour Participation Rate (%)',
    'latitude', 'longitude',
    'Avg_Monthly_Income', 'Avg_Monthly_Expenditure',
    'National_Avg_Personal_Income', 'National_Avg_Disposable_Income', 'National_Avg_Customer_Spend', 'National_Avg_Employment_Salary'
]

# Add dynamically generated average spend, income, and salary features
for col in merged_data.columns:
    if col.startswith('National_Avg_Spend_') or \
       col.startswith('National_Avg_Income_Edu_') or \
       col.startswith('National_Avg_Disposable_Income_Occ_') or \
       col.startswith('National_Avg_Salary_Edu_') or \
       col.startswith('National_Avg_Salary_Job_'):
        features_for_scaling.append(col)

# Drop rows with NaN in features_for_scaling if any remain
merged_data.dropna(subset=features_for_scaling, inplace=True)

# Check if models exist, otherwise train and save them
if os.path.exists(SCALER_PATH) and os.path.exists(KMEANS_PATH) and os.path.exists(RF_MODEL_PATH):
    scaler = joblib.load(SCALER_PATH)
    kmeans = joblib.load(KMEANS_PATH)
    model = joblib.load(RF_MODEL_PATH)
else:
    # Scaling
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(merged_data[features_for_scaling])
    joblib.dump(scaler, SCALER_PATH)

    # KMeans Clustering
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    merged_data['cluster'] = clusters
    joblib.dump(kmeans, KMEANS_PATH)

    # RandomForest Regressor
    X_ml = merged_data[features_for_scaling + ['cluster']]
    y_ml = merged_data['adoption_rate']

    # Add dummy categorical features for OneHotEncoder fitting
    # These will be replaced by actual input in run_prediction_pipeline
    merged_data['product_type'] = 'Electronics' # Placeholder
    merged_data['product_luxury'] = 'Mid-range' # Placeholder
    merged_data['target_audience'] = 'Adults' # Placeholder
    merged_data['price'] = 1000 # Placeholder

    categorical_features = ['product_type', 'product_luxury', 'target_audience']
    onehot_encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
    encoded_features = onehot_encoder.fit_transform(merged_data[categorical_features])
    encoded_feature_names = onehot_encoder.get_feature_names_out(categorical_features)
    encoded_df = pd.DataFrame(encoded_features, columns=encoded_feature_names, index=merged_data.index)
    merged_data = pd.concat([merged_data, encoded_df], axis=1)

    # Update features_for_scaling to include new categorical features and price
    features_for_scaling.extend(encoded_feature_names)
    features_for_scaling.append('price')

    # Ensure all features in features_for_scaling are present in merged_data and handle NaNs
    for feature in features_for_scaling:
        if feature not in merged_data.columns:
            merged_data[feature] = 0 # Add missing feature columns with default 0
    merged_data.dropna(subset=features_for_scaling, inplace=True)

    X_ml = merged_data[features_for_scaling + ['cluster']]
    y_ml = merged_data['adoption_rate']

    model = RandomForestRegressor(random_state=42)
    model.fit(X_ml, y_ml)
    joblib.dump(model, RF_MODEL_PATH)
    joblib.dump(onehot_encoder, os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib'))

    # --- ML Pipeline Function ---

    def run_prediction_pipeline(product_type, product_luxury, target_audience, price, region):

        # Ensure models are loaded (they are loaded globally if they exist)

        global scaler, kmeans, model, merged_data, features_for_scaling, onehot_encoder

        if 'scaler' not in globals() or 'kmeans' not in globals() or 'model' not in globals() or 'onehot_encoder' not in globals():

            if os.path.exists(SCALER_PATH) and os.path.exists(KMEANS_PATH) and os.path.exists(RF_MODEL_PATH) and os.path.exists(os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib')):

                scaler = joblib.load(SCALER_PATH)

                kmeans = joblib.load(KMEANS_PATH)

                model = joblib.load(RF_MODEL_PATH)

                onehot_encoder = joblib.load(os.path.join(ML_MODELS_DIR, 'onehot_encoder.joblib'))

            else:

                raise Exception("ML models not found. Please ensure models are trained and saved.")

    

        # Prepare input features for prediction

        # 1. Get state-level features for the given region

        region_data_row = merged_data[merged_data['State'].str.contains(region, case=False, na=False)]

    

        if region_data_row.empty:

            return {

                'predicted_reach': 0.0,

                'success_probability': 0.0,

                'clusters': [],

                'model_confidence': 0.0,

                'message': f"Region '{region}' not found in demographic data."

            }

    

        # Take the first matching region if multiple exist

        input_features_base = region_data_row.iloc[0][features_for_scaling].to_dict()

    

        # Create input DataFrame for prediction
        input_df_pred = pd.DataFrame([input_features_base])

        # Add price
        input_df_pred['price'] = price

        # Create a DataFrame for categorical inputs
        categorical_input_df = pd.DataFrame([[product_type, product_luxury, target_audience]],
                                            columns=['product_type', 'product_luxury', 'target_audience'])

        # One-hot encode the categorical inputs
        encoded_categorical_features = onehot_encoder.transform(categorical_input_df)
        encoded_categorical_df = pd.DataFrame(encoded_categorical_features, columns=onehot_encoder.get_feature_names_out(categorical_input_df.columns))

        # Concatenate one-hot encoded features
        input_df_pred = pd.concat([input_df_pred, encoded_categorical_df], axis=1)

        # Ensure all features in features_for_scaling are present in input_df_pred
        # and fill missing ones with 0 (important for one-hot encoded columns that might not appear in input)
        for feature in features_for_scaling:
            if feature not in input_df_pred.columns:
                input_df_pred[feature] = 0

        # Reorder columns to match the order used during training
        input_df_pred = input_df_pred[features_for_scaling]

        # Prepare the numerical features for scaling
        input_for_scaling = input_df_pred.values

        # Scale the input features
        input_scaled = scaler.transform(input_for_scaling)

        # Predict the cluster for the input
        input_cluster = kmeans.predict(input_scaled)[0]

        # Prepare input for RandomForestRegressor
        # This needs to match X_ml used during training (features_for_scaling + ['cluster'])
        input_for_rf = np.append(input_scaled[0], input_cluster).reshape(1, -1)

        # Make prediction
        predicted_reach = model.predict(input_for_rf)[0]

    

        # Ensure values are within reasonable bounds

        predicted_reach = max(0.0, min(100.0, predicted_reach))

        success_probability = predicted_reach / 100.0 # Simple conversion

    

        # Generate clusters for visualization (using the predicted cluster's characteristics)

        cluster_centroid = kmeans.cluster_centers_[input_cluster]

        original_features_approx = scaler.inverse_transform(cluster_centroid.reshape(1, -1))[0]

    

        # Find a representative latitude and longitude for the predicted region/state

        # This assumes 'latitude' and 'longitude' columns are added to merged_data during preprocessing

        # For now, I'll use a fixed lat/lon for the region if available, otherwise a default.

        # This is a gap in the current merged_data, which doesn't have lat/lon for states.

        # I will add a placeholder for lat/lon in merged_data during the initial processing.

        # For now, let's use the lat/lon from the first entry of the region_data if available

        if 'latitude' in region_data_row.columns and 'longitude' in region_data_row.columns and not region_data_row.empty:

            cluster_lat = region_data_row['latitude'].iloc[0]

            cluster_lon = region_data_row['longitude'].iloc[0]

        else:

            # Default to approximate center of India if lat/lon not available in merged_data

            cluster_lat = 20.5937

            cluster_lon = 78.9629

    

        predicted_cluster_info = {

            'lat': cluster_lat,

            'lon': cluster_lon,

            'label': f"Cluster {input_cluster}",

            'population_density': original_features_approx[features_for_scaling.index('Density (per km2)')] if 'Density (per km2)' in features_for_scaling else 0,

            'avg_income': original_features_approx[features_for_scaling.index('Overall_Avg_Income')] if 'Overall_Avg_Income' in features_for_scaling else 0,

            'employment_rate': original_features_approx[features_for_scaling.index('Estimated Unemployment Rate (%)')] if 'Estimated Unemployment Rate (%)' in features_for_scaling else 0,

            'interest_index': 0.75 # Placeholder for now

        }

    

        return {

            'predicted_reach': predicted_reach,

            'success_probability': success_probability,

            'clusters': [predicted_cluster_info],

            'model_confidence': 0.85 # Still a placeholder

        }


