from django.shortcuts import render, redirect  # type: ignore
from django.contrib.auth import login, logout, authenticate  # type: ignore
from django.contrib.auth.forms import AuthenticationForm  # type: ignore
from django.contrib.auth.decorators import login_required, user_passes_test  # type: ignore
from django.contrib import messages  # type: ignore
from django.db.models import Count  # type: ignore
from .forms import EntrepreneurRegistrationForm, PredictionRequestForm
from .models import User, PredictionRequest, PredictionResult, Cluster, Dataset
from .ml_pipeline import run_prediction_pipeline
import os
import logging
from geo.views import get_map_context
from charts.views import get_entrepreneur_charts_context, get_admin_charts_context

logger = logging.getLogger(__name__)

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
                    prediction_request = form.save(commit=False)
                    prediction_request.user = request.user
                    prediction_request.save()

                    # Run ML prediction pipeline
                    ml_output = run_prediction_pipeline(
                        product_type=prediction_request.product_type,
                        product_luxury=prediction_request.product_luxury,
                        target_audience=prediction_request.target_audience,
                        price=float(prediction_request.price),
                        region=prediction_request.region
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
                            interest_index=cluster_data.get('interest_index', 0)
                        )

                    messages.success(request, 'Prediction generated successfully!')
                    return redirect('core:entrepreneur_dashboard')
                    
                except Exception as e:
                    logger.error(f"Error generating prediction: {e}")
                    messages.error(request, 'An error occurred while generating the prediction. Please try again.')
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
        charts_context = get_entrepreneur_charts_context()
        
        context = {
            'form': form,
            'past_predictions': past_predictions,
        }
        context.update(map_context)  # Add map data (clusters + config)
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