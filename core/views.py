from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import login, logout, authenticate  # type: ignore
from django.contrib.auth.forms import AuthenticationForm  # type: ignore
from django.contrib.auth.decorators import login_required, user_passes_test  # type: ignore
from django.contrib import messages  # type: ignore
from django.db.models import Count, Avg  # type: ignore
from .forms import EntrepreneurRegistrationForm, PredictionRequestForm
from .models import User, PredictionRequest, PredictionResult, Cluster, Dataset
from .ml_pipeline import run_prediction_pipeline
import os
import logging
import json # Import json to dump the dictionary
from geo.views import get_map_context
from charts.views import get_entrepreneur_charts_context, get_admin_charts_context

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
        form_data = None
        
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

                    # Combine audience-related fields into target_audience
                    target_audience_parts = []
                    if age_group: target_audience_parts.append(f"Age: {age_group}")
                    if gender: target_audience_parts.append(f"Gender: {gender}")
                    if income_range: target_audience_parts.append(f"Income: {income_range}")
                    if education_level: target_audience_parts.append(f"Education: {education_level}")
                    target_audience = ", ".join(target_audience_parts) if target_audience_parts else "General"

                    # Create PredictionRequest instance
                    prediction_request = PredictionRequest(
                        user=request.user,
                        product_type=product_type,
                        product_luxury=product_luxury,
                        target_audience=target_audience,
                        price=price,
                    )
                    prediction_request.save()

                    # Extract form data for map scoring
                    form_data = {
                        'product_type': prediction_request.product_type,
                        'luxury_level': prediction_request.product_luxury,
                        'target_audience': prediction_request.target_audience,
                        'price': float(prediction_request.price)
                    }

                    # Run ML prediction pipeline (existing code)
                    ml_output = run_prediction_pipeline(
                        product_type=prediction_request.product_type,
                        product_luxury=prediction_request.product_luxury,
                        target_audience=prediction_request.target_audience,
                        price=float(prediction_request.price),
                    )

                    prediction_result = PredictionResult.objects.create(
                        prediction_request=prediction_request,
                        predicted_reach=ml_output['predicted_reach'],
                        success_probability=ml_output['success_probability'],
                        model_confidence=ml_output.get('model_confidence', 0.8)
                    )

                    for cluster_data in ml_output['clusters']:
                        Cluster.objects.create(
                            prediction_result=prediction_result,
                            latitude=cluster_data['lat'],
                            longitude=cluster_data['lon'],
                            cluster_label=cluster_data['label'],
                            population_density=cluster_data.get('population_density', 0),
                            avg_income=cluster_data.get('avg_income', 0),
                            employment_rate=cluster_data.get('employment_rate', 0),
                            interest_index=cluster_data.get('interest_index', 0)
                        )

                    messages.success(request, 'Prediction generated successfully!')
                    
                except Exception as e:
                    logger.error(f"Error generating prediction: {e}")
                    messages.error(request, 'An error occurred while generating the prediction. Please try again.')
            else:
                messages.error(request, 'Please correct the errors in the form.')
        else:
            form = PredictionRequestForm()

        try:
            past_predictions = PredictionRequest.objects.filter(user=request.user).order_by('-request_timestamp')
            total_predictions = past_predictions.count()
            
            if total_predictions > 0:
                avg_success_rate = past_predictions.aggregate(
                    avg_success=Avg('predictionresult__success_probability')
                )['avg_success'] or 0
                
                high_potential_count = past_predictions.filter(
                    predictionresult__success_probability__gte=70
                ).count()
                
                medium_potential_count = past_predictions.filter(
                    predictionresult__success_probability__gte=40,
                    predictionresult__success_probability__lt=70
                ).count()
                
                low_potential_count = past_predictions.filter(
                    predictionresult__success_probability__lt=40
                ).count()
            else:
                avg_success_rate = 0
                high_potential_count = 0
                medium_potential_count = 0
                low_potential_count = 0
                
        except Exception as e:
            logger.error(f"Error fetching past predictions: {e}")
            past_predictions = []
            total_predictions = 0
            avg_success_rate = 0
            high_potential_count = 0
            medium_potential_count = 0
            low_potential_count = 0
            messages.warning(request, 'Could not load past predictions.')

        # Get map context - PASS user AND form_data
        map_context = get_map_context(user=request.user, form_data=form_data)
        charts_context = get_entrepreneur_charts_context(user=request.user)
        
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
            'total_predictions': total_predictions,
            'avg_success_rate': round(avg_success_rate, 1),
            'high_potential_count': high_potential_count,
            'medium_potential_count': medium_potential_count,
            'low_potential_count': low_potential_count,
        }
        context.update(map_context)
        context.update(charts_context)
        
        return render(request, 'core/entrepreneur_dashboard.html', context)
    else:
        return redirect('core:admin_dashboard')

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