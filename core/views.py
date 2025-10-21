from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import login, logout, authenticate  # type: ignore
from django.contrib.auth.forms import AuthenticationForm  # type: ignore
from django.contrib.auth.decorators import login_required, user_passes_test  # type: ignore
from django.contrib import messages  # type: ignore
from django.db.models import Count  # type: ignore
from django.db.models import Avg  # type: ignore
from .forms import EntrepreneurRegistrationForm, PredictionRequestForm
from .models import User, PredictionRequest, PredictionResult, Cluster, Dataset
from .ml_pipeline import run_prediction_pipeline
import os
import logging
import json # Import json to dump the dictionary
from geo.views import get_map_context

logger = logging.getLogger(__name__)

# Define product dependencies for dynamic dropdowns
PRODUCT_DEPENDENCIES = {
    'Food': {
        'categories': ['Fast food', 'Organic', 'Packaged', 'Beverages'],
        'sectors': ['Retail', 'Hospitality']
    },
    'Groceries': {
        'categories': ['Daily essentials', 'Organic produce'],
        'sectors': ['Retail']
    },
    'Clothing': {
        'categories': ['Casual wear', 'Formal', 'Ethnic', 'Sportswear'],
        'sectors': ['Fashion', 'Retail']
    },
    'Technology': {
        'categories': ['Smartphones', 'Laptops', 'IoT', 'Appliances'],
        'sectors': ['Telecom', 'Retail']
    },
    'Automobile': {
        'categories': ['Two-wheelers', 'EVs', 'Cars'],
        'sectors': ['Transport', 'Manufacturing']
    },
    'Healthcare': {
        'categories': ['Pharma', 'Wellness', 'Devices'],
        'sectors': ['Health', 'Retail']
    },
    'Education': {
        'categories': ['EdTech', 'Skill training'],
        'sectors': ['Education']
    },
    'Energy': {
        'categories': ['Solar panels', 'Batteries'],
        'sectors': ['Infrastructure']
    },
    'Housing': {
        'categories': ['Real estate', 'Interiors'],
        'sectors': ['Construction']
    },
    'Finance': {
        'categories': ['Insurance', 'Microfinance', 'Credit'],
        'sectors': ['Banking', 'FinTech']
    },
    'Entertainment': {
        'categories': ['Streaming', 'Gaming', 'Cinema'],
        'sectors': ['Media', 'IT']
    },
}

def entrepreneur_register(request):
    if request.method == 'POST':
        form = EntrepreneurRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('core:entrepreneur_dashboard')
    else:
        form = EntrepreneurRegistrationForm()
    return render(request, 'core/entrepreneur_register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Type hint to help VS Code recognize the custom User model
                user_obj: User = user  # type: ignore
                if user_obj.is_blocked:
                    messages.error(request, 'Your account has been blocked. Please contact an administrator.')
                    return render(request, 'core/login.html', {'form': form})
                
                login(request, user)
                if user.is_superuser:
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('core:admin_dashboard')
                else:
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('core:entrepreneur_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})

@login_required
def user_logout(request):
    logout(request)
    return redirect('core:login')

@login_required
def entrepreneur_dashboard(request):
    if not request.user.is_superuser:
        if request.method == 'POST':
            form = PredictionRequestForm(request.POST)
            if form.is_valid():
                try:
                    # Extract data from the form, including new dropdowns
                    product_type = form.cleaned_data['product_type']
                    product_luxury = form.cleaned_data['product_luxury']
                    product_category = form.cleaned_data.get('product_category', '')
                    sector = form.cleaned_data.get('sector', '')
                    age_group = form.cleaned_data.get('age_group', '')
                    gender = form.cleaned_data.get('gender', '')
                    income_range = form.cleaned_data.get('income_range', '')
                    education_level = form.cleaned_data.get('education_level', '')
                    price = form.cleaned_data.get('price', 0.0) # Directly get price
                    
                    # Validate price
                    if not price or price <= 0:
                        messages.error(request, 'Please enter a valid price greater than 0.')
                        raise ValueError('Invalid price')

                    # Combine audience-related fields into target_audience
                    target_audience_parts = []
                    if age_group: target_audience_parts.append(f"Age: {age_group}")
                    if gender: target_audience_parts.append(f"Gender: {gender}")
                    if income_range: target_audience_parts.append(f"Income: {income_range}")
                    if education_level: target_audience_parts.append(f"Education: {education_level}")
                    target_audience = ", ".join(target_audience_parts) if target_audience_parts else "General"

                    # Determine region based on product type (default to "India" for now)
                    region = "India"  # Can be enhanced to be more specific based on clusters

                    # Create PredictionRequest instance
                    prediction_request = PredictionRequest(
                        user=request.user,
                        product_type=product_type,
                        product_luxury=product_luxury,
                        target_audience=target_audience,
                        price=price,
                        region=region,
                    )
                    prediction_request.save()

                    # Run ML prediction pipeline
                    ml_output = run_prediction_pipeline(
                        product_type=prediction_request.product_type,
                        product_luxury=prediction_request.product_luxury,
                        target_audience=prediction_request.target_audience,
                        price=float(prediction_request.price),
                        region=prediction_request.region,
                    )

                    # Save PredictionResult
                    prediction_result = PredictionResult.objects.create(
                        prediction_request=prediction_request,
                        predicted_reach=ml_output['predicted_reach'],
                        success_probability=ml_output['success_probability'],
                        model_confidence=ml_output.get('model_confidence', 0.8)
                    )

                    # Save Clusters
                    for cluster_data in ml_output['clusters']:
                        Cluster.objects.create(
                            prediction_result=prediction_result,
                            latitude=cluster_data['lat'],
                            longitude=cluster_data['lon'],
                            cluster_label=cluster_data['label'],
                            population_density=cluster_data.get('population_density', 0),
                            avg_income=cluster_data.get('avg_income', 0),
                            employment_rate=cluster_data.get('employment_rate', 0),
                            interest_index=cluster_data.get('interest_index', 0),
                            city_name=cluster_data.get('city_name', ''),
                            state=cluster_data.get('state', ''),
                            tier=cluster_data.get('tier', 0),
                            population=cluster_data.get('population', 0),
                            literacy_rate=cluster_data.get('literacy_rate', 0),
                            relevant_expenditure=cluster_data.get('relevant_expenditure', 0)
                        )

                    messages.success(request, 'Prediction generated successfully!')
                    # Redirect to analytics page instead of dashboard
                    return redirect('core:prediction_analytics', prediction_id=prediction_request.id)
                    
                except ValueError as ve:
                    # Validation errors
                    logger.error(f"Validation error in prediction: {ve}")
                    messages.error(request, f'Validation error: {str(ve)}')
                except KeyError as ke:
                    # Missing keys in ML output
                    logger.error(f"ML output missing key: {ke}")
                    messages.error(request, 'ML prediction incomplete. Please contact support.')
                except Exception as e:
                    # General errors
                    logger.error(f"Error generating prediction: {e}", exc_info=True)
                    messages.error(request, f'An error occurred while generating the prediction: {str(e)}. Please try again.')
            else:
                messages.error(request, 'Please correct the errors in the form.')
        else:
            form = PredictionRequestForm()

        try:
            past_predictions = PredictionRequest.objects.filter(user=request.user).order_by('-request_timestamp')
        except Exception as e:
            logger.error(f"Error fetching past predictions: {e}")
            past_predictions = []
            messages.warning(request, 'Could not load past predictions.')

        map_context = get_map_context(request.GET)  # Get enhanced map data from geo app
        
        context = {
            'form': form,
            'past_predictions': past_predictions,
            # Pass choices for dropdowns to the template
            'product_type_choices': PredictionRequestForm.PRODUCT_TYPE_CHOICES,
            'product_luxury_choices': PredictionRequestForm.LUXURY_LEVEL_CHOICES,
            'product_category_choices': PredictionRequestForm.PRODUCT_CATEGORY_CHOICES,
            'sector_choices': PredictionRequestForm.SECTOR_CHOICES,
            'age_group_choices': PredictionRequestForm.AGE_GROUP_CHOICES,
            'gender_choices': PredictionRequestForm.GENDER_CHOICES,
            'income_range_choices': PredictionRequestForm.INCOME_RANGE_CHOICES,
            'education_level_choices': PredictionRequestForm.EDUCATION_LEVEL_CHOICES,
            'product_dependencies_json': json.dumps(PRODUCT_DEPENDENCIES), # Pass the dependencies as JSON
        }
        context.update(map_context)  # Add map data (clusters + config)
        
        return render(request, 'core/entrepreneur_dashboard.html', context)
    else:
        return redirect('core:admin_dashboard')

@login_required
def past_predictions(request):
    """View for displaying all past predictions for entrepreneurs"""
    if request.user.is_superuser:
        return redirect('core:admin_dashboard')
    
    try:
        past_predictions = PredictionRequest.objects.filter(
            user=request.user
        ).select_related('predictionresult').order_by('-request_timestamp')
        
        # Calculate statistics
        predictions_with_results = past_predictions.filter(predictionresult__isnull=False)
        
        if predictions_with_results.exists():
            avg_reach = predictions_with_results.aggregate(
                avg=Avg('predictionresult__predicted_reach')
            )['avg'] or 0
            
            avg_probability = predictions_with_results.aggregate(
                avg=Avg('predictionresult__success_probability')
            )['avg'] or 0
            
            avg_price = past_predictions.aggregate(avg=Avg('price'))['avg'] or 0
        else:
            avg_reach = 0
            avg_probability = 0
            avg_price = 0
        
        context = {
            'past_predictions': past_predictions,
            'avg_reach': avg_reach,
            'avg_probability': avg_probability,
            'avg_price': avg_price,
        }
        
        return render(request, 'core/past_predictions.html', context)
        
    except Exception as e:
        logger.error(f"Error fetching past predictions: {e}")
        messages.error(request, 'An error occurred while loading past predictions.')
        return redirect('core:entrepreneur_dashboard')

@login_required
def prediction_analytics(request, prediction_id):
    """Detailed analytics view for a specific prediction"""
    if request.user.is_superuser:
        return redirect('core:admin_dashboard')
    
    try:
        # Get the prediction request
        prediction = PredictionRequest.objects.get(id=prediction_id, user=request.user)
        
        # Get the prediction result
        try:
            result = prediction.predictionresult
        except PredictionResult.DoesNotExist:
            messages.error(request, 'Prediction result not yet available.')
            return redirect('core:entrepreneur_dashboard')
        
        # Get clusters
        clusters = Cluster.objects.filter(prediction_result=result)
        
        # Prepare cluster data for map
        clusters_data = []
        for cluster in clusters:
            try:
                # Handle both old clusters (without new fields) and new clusters (with new fields)
                clusters_data.append({
                    'lat': float(cluster.latitude),
                    'lon': float(cluster.longitude),
                    'label': cluster.cluster_label,
                    'city_name': cluster.city_name or '',
                    'state': cluster.state or '',
                    'tier': cluster.tier or 0,
                    'population': cluster.population or 0,
                    'population_density': cluster.population_density or 0,
                    'avg_income': float(cluster.avg_income) if cluster.avg_income else 0,
                    'literacy_rate': float(cluster.literacy_rate) if cluster.literacy_rate else 0,
                    'employment_rate': float(cluster.employment_rate) if cluster.employment_rate else 0,
                    'interest_index': float(cluster.interest_index) if cluster.interest_index else 0,
                    'relevant_expenditure': float(cluster.relevant_expenditure) if cluster.relevant_expenditure else 0
                })
            except Exception as e:
                logger.error(f"Error processing cluster {cluster.id}: {e}")
                # Add minimal cluster data to avoid breaking the page
                clusters_data.append({
                    'lat': float(cluster.latitude),
                    'lon': float(cluster.longitude),
                    'label': cluster.cluster_label,
                    'city_name': '',
                    'state': '',
                    'tier': 0,
                    'population': 0,
                    'population_density': cluster.population_density or 0,
                    'avg_income': float(cluster.avg_income) if cluster.avg_income else 0,
                    'literacy_rate': 0,
                    'employment_rate': float(cluster.employment_rate) if cluster.employment_rate else 0,
                    'interest_index': float(cluster.interest_index) if cluster.interest_index else 0,
                    'relevant_expenditure': 0
                })
        
        # Get top districts dynamically from cluster data
        top_districts = get_top_districts_for_product(
            clusters_data=clusters_data,
            product_type=prediction.product_type,
            product_luxury=prediction.product_luxury,
            target_audience=prediction.target_audience,
            price=float(prediction.price)
        )
        
        # Get economic indicators from cluster data
        economic_indicators = get_economic_indicators_for_prediction(clusters_data)
        
        # Parse target audience and generate demographics from cluster data
        demographic_labels, demographic_values = parse_target_audience(
            prediction.target_audience,
            clusters_data,
            prediction.product_type
        )
        
        # Aggregate state-level data
        state_level_data = aggregate_state_level_data(clusters_data)
        
        # Generate state-level demographics from aggregated state data
        state_demographic_labels, state_demographic_values = parse_target_audience(
            prediction.target_audience,
            state_level_data,
            prediction.product_type
        )
        
        context = {
            'prediction': prediction,
            'result': result,
            'clusters': clusters,
            'clusters_json': json.dumps(clusters_data),
            'state_level_json': json.dumps(state_level_data),
            'top_districts': top_districts,
            'economic_indicators': economic_indicators,
            'demographic_labels': json.dumps(demographic_labels),
            'demographic_values': json.dumps(demographic_values),
            'state_demographic_labels': json.dumps(state_demographic_labels),
            'state_demographic_values': json.dumps(state_demographic_values),
        }
        
        return render(request, 'core/prediction_analytics.html', context)
        
    except PredictionRequest.DoesNotExist:
        messages.error(request, 'Prediction not found.')
        return redirect('core:entrepreneur_dashboard')
    except Exception as e:
        import traceback
        logger.error(f"Error loading prediction analytics: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, f'An error occurred while loading analytics: {str(e)}')
        return redirect('core:entrepreneur_dashboard')


def calculate_potential_label(score):
    """
    Map market_score or normalized value to 12-level granular label
    
    Args:
        score: Can be market_score (45-97) or normalized percentage (0-100)
    
    Returns:
        String label: 'Very High', 'High+', 'High', 'Medium+', 'Medium', 
                      'Medium-', 'Low+', 'Low', 'Very Low'
    
    Mapping Strategy:
        market_score range is 45.02 to 97.45 (from dataset)
        We treat this as-is: score itself represents percentage potential
        
        12-Level Breakdown:
        - Very High: ≥80%  (Excellent market potential)
        - High+:     70-80% (Strong potential, upper tier)
        - High:      70%+   (alias for High+, user-requested)
        - Medium+:   50-70% (Good potential, upper medium)
        - Medium:    40-50% (Moderate potential)
        - Medium-:   40-45% (Fair potential, lower medium)
        - Low+:      30-40% (Limited but viable)
        - Low:       20-30% (Low potential)
        - Very Low:  <20%   (Minimal potential)
    """
    # Treat score as percentage directly
    percentage = float(score)
    
    # Apply 12-level granular labels
    # Note: We use 8 distinct labels (High+ covers "High" tier)
    if percentage >= 80:
        return 'Very High'
    elif percentage >= 70:
        return 'High+'  # Covers both "High+" and "High"
    elif percentage >= 50:
        return 'Medium+'
    elif percentage >= 45:
        return 'Medium'
    elif percentage >= 40:
        return 'Medium-'
    elif percentage >= 30:
        return 'Low+'
    elif percentage >= 20:
        return 'Low'
    else:  # < 20%
        return 'Very Low'


@login_required
def get_reachability_geojson(request, prediction_id):
    """
    Generate GeoJSON with market potential data for polygon overlay
    
    Strategy:
    1. Base Layer: MarketPotentialZone.market_score (45-97) gives inherent potential
       - Every district has inherent market characteristics independent of predictions
       - Scores mapped to 12-level granular labels
    2. Optional Overlay: Cluster data from predictions (if available)
       - Provides prediction-specific interest_index
       - Can overlay/modify base potential
    
    Uses spatial queries to match data with district/state boundaries
    Returns geographic boundaries colored by potential level
    """
    from django.http import JsonResponse
    from django.contrib.gis.geos import Point
    from django.db.models import Avg, Count, Q
    from collections import defaultdict
    import geopandas as gpd
    import traceback
    from shapely.geometry import shape, Point as ShapelyPoint
    from geo.models import MarketPotentialZone
    
    try:
        logger.info(f"GeoJSON request for prediction {prediction_id}, granularity: {request.GET.get('granularity', 'district')}")
        
        # Get prediction and result
        prediction = PredictionRequest.objects.get(id=prediction_id, user=request.user)
        result = PredictionResult.objects.filter(prediction_request=prediction).first()
        
        if not result:
            return JsonResponse({'error': 'No result found'}, status=404)
        
        # Get clusters with reachability data
        clusters = Cluster.objects.filter(prediction_result=result)
        logger.info(f"Processing {clusters.count()} clusters")
        
        # Get granularity parameter (district or state)
        granularity = request.GET.get('granularity', 'district')
        
        # Load shapefiles
        shapefile_dir = os.path.join('datasets', 'geodata')
        
        if granularity == 'state':
            # Load state boundaries
            shapefile_path = os.path.join(shapefile_dir, 'india_states.shp')
            gdf = gpd.read_file(shapefile_path)
            logger.info(f"Loaded {len(gdf)} state boundaries")
            
            # STEP 1: Load inherent market potential from MarketPotentialZone dataset
            gdf['market_score'] = None
            gdf['interest_index'] = None
            gdf['label'] = None
            gdf['cluster_count'] = 0
            gdf['matched_clusters'] = [[] for _ in range(len(gdf))]
            
            # Calculate state-level potential by aggregating district data
            logger.info("Calculating state-level potential from district aggregation...")
            from geo.models import State as GeoState, District as GeoDistrict
            from core.utils.potential_calculator import calculate_district_potential, calculate_district_reachability
            
            for idx, row in gdf.iterrows():
                state_name = row.get('NAME_1') or row.get('name') or row.get('STATE')
                
                if state_name:
                    # Get State model instance
                    geo_state = GeoState.objects.filter(name__iexact=state_name.strip()).first()
                    
                    if geo_state:
                        # Get all districts in this state
                        state_districts = GeoDistrict.objects.filter(state=geo_state)
                        
                        if state_districts.exists():
                            # Calculate potential for each district and average
                            district_potentials = []
                            district_reachabilities = []
                            
                            for district in state_districts:
                                try:
                                    potential = calculate_district_potential(
                                        district=district,
                                        state=geo_state,
                                        product_category=prediction.product_type,
                                        target_age_group=getattr(prediction, 'target_age_group', None)
                                    )
                                    reachability = calculate_district_reachability(
                                        district=district,
                                        state=geo_state,
                                        product_category=prediction.product_type,
                                        prediction=prediction
                                    )
                                    district_potentials.append(potential)
                                    district_reachabilities.append(reachability)
                                except Exception as e:
                                    logger.warning(f"Error calculating for district {district.name}: {e}")
                            
                            if district_potentials:
                                # Average across all districts in state
                                avg_potential = sum(district_potentials) / len(district_potentials)
                                avg_reachability = sum(district_reachabilities) / len(district_reachabilities)
                                
                                gdf.at[idx, 'market_score'] = avg_potential
                                gdf.at[idx, 'label'] = calculate_potential_label(avg_potential)
                                gdf.at[idx, 'interest_index'] = avg_reachability
                                
                                logger.info(f"State {state_name}: avg_potential={avg_potential:.2f}, avg_reachability={avg_reachability:.3f}, label={gdf.at[idx, 'label']}")
            
            states_with_data = gdf['market_score'].notna().sum()
            logger.info(f"{states_with_data} out of {len(gdf)} states have calculated potential data")
            
            # STEP 2 (Optional): Overlay cluster data if available
            for cluster in clusters:
                if cluster.latitude and cluster.longitude:
                    point = ShapelyPoint(float(cluster.longitude), float(cluster.latitude))
                    
                    # Check which state polygon contains this point
                    for idx, row in gdf.iterrows():
                        if row['geometry'].contains(point):
                            if cluster.interest_index is not None:
                                gdf.at[idx, 'matched_clusters'].append({
                                    'interest_index': float(cluster.interest_index),
                                    'label': cluster.cluster_label
                                })
                            break
            
            # STEP 3: Combine base market_score with cluster data (if available)
            states_with_clusters = 0
            states_base_only = 0
            states_no_data = 0
            
            for idx, row in gdf.iterrows():
                matched = gdf.at[idx, 'matched_clusters']
                
                if matched:
                    # Has cluster data - use it (prediction-specific)
                    avg_interest = sum(c['interest_index'] for c in matched) / len(matched)
                    gdf.at[idx, 'interest_index'] = avg_interest
                    gdf.at[idx, 'cluster_count'] = len(matched)
                    gdf.at[idx, 'label'] = calculate_potential_label(avg_interest * 100)
                    states_with_clusters += 1
                    
                    logger.info(f"State {row['NAME_1']}: {len(matched)} clusters, avg interest: {avg_interest:.3f}, label: {gdf.at[idx, 'label']}")
                
                elif gdf.at[idx, 'market_score'] is not None:
                    # No clusters, but has base market_score - keep it
                    states_base_only += 1
                else:
                    # No clusters AND no market_score - truly no data
                    states_no_data += 1
            
            logger.info(f"States: {states_with_clusters} with clusters, {states_base_only} base market data only, {states_no_data} no data")
            
            # Remove temporary column
            gdf = gdf.drop(columns=['matched_clusters'])
            
        else:  # district level
            # Load district boundaries
            shapefile_path = os.path.join(shapefile_dir, 'india_districts.shp')
            gdf = gpd.read_file(shapefile_path)
            logger.info(f"Loaded {len(gdf)} district boundaries")
            
            # STEP 1: Calculate market potential from database fields
            # Uses demographic, economic, and geographic data specific to product category
            gdf['market_score'] = None  # Will store calculated potential score
            gdf['interest_index'] = None  # Will store calculated reachability (or cluster if available)
            gdf['label'] = None  # Potential label (calculated from scores)
            gdf['cluster_count'] = 0
            gdf['matched_clusters'] = [[] for _ in range(len(gdf))]
            
            # Import calculation functions
            logger.info("Calculating district potential from database fields...")
            from geo.models import District as GeoDistrict
            from core.utils.potential_calculator import calculate_district_potential, calculate_district_reachability
            
            for idx, row in gdf.iterrows():
                district_name = row.get('DISTRICT') or row.get('NAME_2') or row.get('name')
                state_name = row.get('STATE') or row.get('NAME_1') or row.get('state')
                
                if district_name and state_name:
                    # Handle state name variations
                    state_name_variations = [
                        state_name.strip(),
                        state_name.strip() + " Islands" if "Andaman" in state_name else state_name.strip(),
                        "Dadra and Nagar Haveli and Daman and Diu" if "Dadra" in state_name or "Daman" in state_name else state_name.strip(),
                        "Delhi" if "NCT" in state_name or "National Capital" in state_name else state_name.strip(),
                    ]
                    
                    # Try to find district with any state name variation
                    geo_district = None
                    for state_variant in state_name_variations:
                        geo_district = GeoDistrict.objects.filter(
                            name__iexact=district_name.strip(),
                            state__name__iexact=state_variant
                        ).first()
                        if geo_district:
                            break
                    
                    # If still not found, try fuzzy match on district name only
                    if not geo_district:
                        geo_district = GeoDistrict.objects.filter(
                            name__iexact=district_name.strip()
                        ).first()
                    
                    if geo_district:
                        # Calculate potential from database fields (demographics, economics, etc.)
                        calculated_potential = calculate_district_potential(
                            district=geo_district,
                            state=geo_district.state,
                            product_category=prediction.product_type,
                            target_age_group=getattr(prediction, 'target_age_group', None)
                        )
                        
                        # Calculate reachability (potential × accessibility × demographic_match)
                        calculated_reachability = calculate_district_reachability(
                            district=geo_district,
                            state=geo_district.state,
                            product_category=prediction.product_type,
                            prediction=prediction
                        )
                        
                        gdf.at[idx, 'market_score'] = calculated_potential
                        gdf.at[idx, 'label'] = calculate_potential_label(calculated_potential)
                        gdf.at[idx, 'interest_index'] = calculated_reachability
                        
                        logger.info(f"District {district_name}, {state_name}: calculated_potential={calculated_potential:.2f}, reachability={calculated_reachability:.3f}, label={gdf.at[idx, 'label']}")
            
            districts_with_market_data = gdf['market_score'].notna().sum()
            logger.info(f"{districts_with_market_data} out of {len(gdf)} districts have market potential data")
            
            # STEP 2 (Optional): Overlay cluster data if available
            # Clusters provide prediction-specific interest scores
            # If clusters exist, they can modify the base market potential
            matched_count = 0
            for cluster in clusters:
                if cluster.latitude and cluster.longitude:
                    point = ShapelyPoint(float(cluster.longitude), float(cluster.latitude))
                    
                    # Check which district polygon contains this point
                    for idx, row in gdf.iterrows():
                        if row['geometry'].contains(point):
                            # Only add cluster if it has valid interest_index
                            if cluster.interest_index is not None:
                                gdf.at[idx, 'matched_clusters'].append({
                                    'interest_index': float(cluster.interest_index),
                                    'label': cluster.cluster_label
                                })
                                matched_count += 1
                            break
            
            logger.info(f"Matched {matched_count} out of {clusters.count()} clusters to districts")
            
            # STEP 3: Combine base market_score with cluster data (if available)
            # Priority: If clusters exist for a district, use their average
            # Otherwise: Keep the base market_score from MarketPotentialZone
            districts_with_clusters = 0
            districts_base_only = 0
            districts_no_data = 0
            
            for idx, row in gdf.iterrows():
                matched = gdf.at[idx, 'matched_clusters']
                
                if matched:
                    # Has cluster data - use it (prediction-specific)
                    avg_interest = sum(c['interest_index'] for c in matched) / len(matched)
                    gdf.at[idx, 'interest_index'] = avg_interest
                    gdf.at[idx, 'cluster_count'] = len(matched)
                    
                    # Calculate label from cluster interest (convert from 0-1 to 0-100)
                    gdf.at[idx, 'label'] = calculate_potential_label(avg_interest * 100)
                    districts_with_clusters += 1
                    
                    logger.info(f"District has clusters: interest={avg_interest:.3f}, label={gdf.at[idx, 'label']}")
                
                elif gdf.at[idx, 'market_score'] is not None:
                    # No clusters, but has base market_score - keep it
                    # market_score and label already set in STEP 1
                    districts_base_only += 1
                else:
                    # No clusters AND no market_score - truly no data
                    districts_no_data += 1
            
            logger.info(f"Districts: {districts_with_clusters} with clusters, {districts_base_only} base market data only, {districts_no_data} no data")
            
            # Remove temporary column
            gdf = gdf.drop(columns=['matched_clusters'])
        
        # Simplify geometry for faster rendering
        logger.info(f"Converting {len(gdf)} features to GeoJSON...")
        gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.01, preserve_topology=True)
        
        # Convert to GeoJSON
        geojson = json.loads(gdf.to_json())
        logger.info(f"GeoJSON generated successfully with {len(geojson.get('features', []))} features")
        
        return JsonResponse(geojson, safe=False)
        
    except Exception as e:
        logger.error(f"Error generating GeoJSON: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'error': str(e)}, status=500)


def get_top_districts_for_product(clusters_data, product_type, product_luxury, target_audience, price):
    """
    Get top districts dynamically from cluster data
    Returns districts sorted by interest index (highest potential first)
    """
    districts = []
    
    # Convert cluster data to district format
    for cluster in clusters_data:
        # Only include clusters with city information
        if cluster.get('city_name'):
            district_info = {
                'name': cluster['city_name'],
                'state': cluster['state'],
                'population': cluster['population'],
                'avg_income': cluster['avg_income'],
                'lat': cluster['lat'],
                'lon': cluster['lon'],
                'interest_index': cluster['interest_index'],
                'label': cluster['label'],
                'tier': cluster.get('tier', 0),
                'literacy_rate': cluster.get('literacy_rate', 0),
                'employment_rate': cluster.get('employment_rate', 0),
                'population_density': cluster.get('population_density', 0)
            }
            districts.append(district_info)
    
    # Sort by interest index (highest first)
    districts.sort(key=lambda x: x['interest_index'], reverse=True)
    
    # Return top 5 districts
    return districts[:5]


def aggregate_state_level_data(clusters_data):
    """
    Aggregate cluster data by state for state-level view
    Returns state-level aggregated data with average metrics
    """
    from collections import defaultdict
    
    state_aggregates = defaultdict(lambda: {
        'clusters': [],
        'total_population': 0,
        'total_income': 0,
        'total_employment': 0,
        'total_literacy': 0,
        'total_interest': 0,
        'count': 0
    })
    
    # Group clusters by state
    for cluster in clusters_data:
        if cluster.get('state'):
            state = cluster['state']
            agg = state_aggregates[state]
            
            agg['clusters'].append(cluster)
            agg['total_population'] += cluster.get('population', 0)
            agg['total_income'] += cluster.get('avg_income', 0)
            agg['total_employment'] += cluster.get('employment_rate', 0)
            agg['total_literacy'] += cluster.get('literacy_rate', 0)
            agg['total_interest'] += cluster.get('interest_index', 0)
            agg['count'] += 1
    
    # Calculate averages and determine state-level potential
    state_level_data = []
    for state, agg in state_aggregates.items():
        count = agg['count']
        avg_interest = agg['total_interest'] / count if count > 0 else 0
        
        # Determine state-level label based on average interest
        if avg_interest >= 0.65:
            label = 'High'
        elif avg_interest >= 0.40:
            label = 'Medium'
        else:
            label = 'Low'
        
        # Calculate center point (average of all cluster coordinates)
        avg_lat = sum(c['lat'] for c in agg['clusters']) / count
        avg_lon = sum(c['lon'] for c in agg['clusters']) / count
        
        state_data = {
            'state': state,
            'center_lat': round(avg_lat, 4),
            'center_lon': round(avg_lon, 4),
            'label': label,
            'avg_population': round(agg['total_population'] / count) if count > 0 else 0,
            'avg_income': round(agg['total_income'] / count, 2) if count > 0 else 0,
            'avg_employment_rate': round(agg['total_employment'] / count, 2) if count > 0 else 0,
            'avg_literacy_rate': round(agg['total_literacy'] / count, 2) if count > 0 else 0,
            'interest_index': round(avg_interest, 3),
            'district_count': count,
            'top_district': max(agg['clusters'], key=lambda x: x.get('interest_index', 0))['city_name'] if agg['clusters'] else ''
        }
        state_level_data.append(state_data)
    
    # Sort by interest index
    state_level_data.sort(key=lambda x: x['interest_index'], reverse=True)
    
    return state_level_data


def get_economic_indicators_for_prediction(clusters_data):
    """
    Get economic indicators dynamically from cluster data
    Returns key economic metrics for each cluster
    """
    indicators = []
    
    for cluster in clusters_data:
        if cluster.get('city_name'):
            indicator = {
                'district': cluster['city_name'],
                'state': cluster['state'],
                'avg_income': cluster['avg_income'],
                'unemployment': round(100 - cluster.get('employment_rate', 95), 1),  # Calculate from employment rate
                'literacy_rate': cluster.get('literacy_rate', 0),
                'population': cluster.get('population', 0),
                'relevant_expenditure': cluster.get('relevant_expenditure', 0),
                'label': cluster['label']
            }
            indicators.append(indicator)
    
    # Sort by income (highest first) for display
    indicators.sort(key=lambda x: x['avg_income'], reverse=True)
    
    return indicators


def parse_target_audience(target_audience_str, clusters_data, product_type):
    """
    Parse target audience and generate demographic insights from cluster or state data
    Returns labels and values for demographic chart
    Handles both district-level (clusters) and state-level (aggregated) data
    """
    labels = []
    values = []
    
    # Calculate average metrics across clusters or states
    if clusters_data:
        # Check if this is state-level data (has 'avg_literacy_rate') or district-level (has 'literacy_rate')
        is_state_data = len(clusters_data) > 0 and 'avg_literacy_rate' in clusters_data[0]
        
        if is_state_data:
            # State-level data
            avg_literacy = sum(c.get('avg_literacy_rate', 0) for c in clusters_data) / len(clusters_data)
            avg_employment = sum(c.get('avg_employment_rate', 0) for c in clusters_data) / len(clusters_data)
            avg_income = sum(c.get('avg_income', 0) for c in clusters_data) / len(clusters_data)
        else:
            # District-level data
            avg_literacy = sum(c.get('literacy_rate', 0) for c in clusters_data) / len(clusters_data)
            avg_employment = sum(c.get('employment_rate', 0) for c in clusters_data) / len(clusters_data)
            avg_income = sum(c.get('avg_income', 0) for c in clusters_data) / len(clusters_data)
        
        # Count cluster/state types
        high_potential = sum(1 for c in clusters_data if c.get('label') == 'High')
        medium_potential = sum(1 for c in clusters_data if c.get('label') == 'Medium')
        low_potential = sum(1 for c in clusters_data if c.get('label') == 'Low')
        total_clusters = len(clusters_data)
        
        # Create demographic distribution based on actual data
        labels = [
            'High Potential Areas',
            'Medium Potential Areas',
            'Low Potential Areas',
            'Literacy Rate (avg)',
            'Employment Rate (avg)'
        ]
        
        values = [
            round((high_potential / total_clusters) * 100, 1) if total_clusters > 0 else 0,
            round((medium_potential / total_clusters) * 100, 1) if total_clusters > 0 else 0,
            round((low_potential / total_clusters) * 100, 1) if total_clusters > 0 else 0,
            round(avg_literacy, 1),
            round(avg_employment, 1)
        ]
    
    # Enhance with target audience parsing
    audience_lower = target_audience_str.lower()
    
    # Age group detection
    if 'young' in audience_lower or '18-25' in audience_lower or '20-30' in audience_lower:
        labels.insert(0, 'Young Adults (18-30)')
        values.insert(0, 35)
    elif 'middle' in audience_lower or '30-45' in audience_lower or '35-50' in audience_lower:
        labels.insert(0, 'Middle Age (30-50)')
        values.insert(0, 40)
    elif 'senior' in audience_lower or 'elderly' in audience_lower or '50+' in audience_lower:
        labels.insert(0, 'Senior (50+)')
        values.insert(0, 25)
    
    # Income level detection
    if 'high income' in audience_lower or 'affluent' in audience_lower or 'premium' in audience_lower:
        if avg_income > 60000:
            values[0] = min(values[0] * 1.2, 100) if values else 70  # Boost if income matches
    elif 'low income' in audience_lower or 'budget' in audience_lower or 'affordable' in audience_lower:
        if avg_income < 40000:
            values[0] = min(values[0] * 1.2, 100) if values else 60
    
    # Default if nothing parsed
    if not labels:
        labels = ['Urban Population', 'Working Class', 'Middle Income', 'Tech-Savvy']
        values = [70, 65, 60, 55]
    
    return labels, values

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    total_users = User.objects.count()
    total_predictions = PredictionRequest.objects.count()

    # Most queried regions
    most_queried_regions = PredictionRequest.objects.values('region')\
                                            .annotate(count=Count('region'))\
                                            .order_by('-count')[:5]

    # Dataset & model version
    latest_datasets = Dataset.objects.order_by('-upload_date')[:5]
    
    # List ML model files
    ml_model_dir = os.path.join(os.path.dirname(__file__), 'models_ml')
    ml_model_files = [f for f in os.listdir(ml_model_dir) if os.path.isfile(os.path.join(ml_model_dir, f))]

    context = {
        'total_users': total_users,
        'total_predictions': total_predictions,
        'most_queried_regions': most_queried_regions,
        'latest_datasets': latest_datasets,
        'ml_model_files': ml_model_files,
    }
    return render(request, 'core/admin_dashboard.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def dataset_management(request):
    """Dataset management view for admins"""
    datasets = Dataset.objects.all().order_by('-upload_date')
    
    context = {
        'datasets': datasets,
    }
    return render(request, 'core/dataset_management.html', context)

@login_required
@user_passes_test(lambda u: u.is_superuser)
def user_management(request):
    """User management view for admins"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        try:
            user = User.objects.get(id=user_id)
            if action == 'block':
                user.is_blocked = True
                user.save()
                messages.success(request, f'User {user.username} has been blocked.')
            elif action == 'unblock':
                user.is_blocked = False
                user.save()
                messages.success(request, f'User {user.username} has been unblocked.')
            elif action == 'deactivate':
                user.is_active = False
                user.save()
                messages.success(request, f'User {user.username} has been deactivated.')
            elif action == 'activate':
                user.is_active = True
                user.save()
                messages.success(request, f'User {user.username} has been activated.')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
        except Exception as e:
            logger.error(f"Error in user management: {e}")
            messages.error(request, 'An error occurred while processing the request.')
    
    users = User.objects.all().order_by('username')
    
    context = {
        'users': users,
    }
    return render(request, 'core/user_management.html', context)