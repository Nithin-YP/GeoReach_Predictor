from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, PredictionRequest

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'is_blocked')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff', 'is_superuser', 'is_blocked', 'groups', 'user_permissions')

class EntrepreneurRegistrationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

class PredictionRequestForm(forms.ModelForm):
    class Meta:
        model = PredictionRequest
        fields = ['product_type', 'product_luxury', 'target_audience', 'price', 'region']
