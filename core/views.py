from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import EntrepreneurRegistrationForm, PredictionRequestForm
from .models import User, PredictionRequest, PredictionResult, Cluster
from .ml_pipeline import run_prediction_pipeline

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
                login(request, user)
                if user.is_superuser:
                    return redirect('core:admin_dashboard')
                else:
                    return redirect('core:entrepreneur_dashboard')
            else:
                # Invalid login credentials
                pass # Add error message handling here
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
                    model_confidence=ml_output['model_confidence']
                )

                # Save Clusters
                for cluster_data in ml_output['clusters']:
                    Cluster.objects.create(
                        prediction_result=prediction_result,
                        latitude=cluster_data['lat'],
                        longitude=cluster_data['lon'],
                        cluster_label=cluster_data['label'],
                        population_density=cluster_data['population_density'],
                        avg_income=cluster_data['avg_income'],
                        employment_rate=cluster_data['employment_rate'],
                        interest_index=cluster_data['interest_index']
                    )

                return redirect('core:entrepreneur_dashboard') # Redirect to clear form
        else:
            form = PredictionRequestForm()

        past_predictions = PredictionRequest.objects.filter(user=request.user).order_by('-request_timestamp')
        context = {
            'form': form,
            'past_predictions': past_predictions,
        }
        return render(request, 'core/entrepreneur_dashboard.html', context)
    else:
        return redirect('core:admin_dashboard') # Admins shouldn't access entrepreneur dashboard

@login_required
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    return render(request, 'core/admin_dashboard.html')