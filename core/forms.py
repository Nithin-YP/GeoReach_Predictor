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
    PRODUCT_TYPE_CHOICES = [
        ('Food', 'Food'),
        ('Groceries', 'Groceries'),
        ('Clothing', 'Clothing'),
        ('Technology', 'Technology'),
        ('Automobile', 'Automobile'),
        ('Healthcare', 'Healthcare'),
        ('Education', 'Education'),
        ('Energy', 'Energy'),
        ('Housing', 'Housing'),
        ('Finance', 'Finance'),
        ('Entertainment', 'Entertainment'),
    ]

    PRODUCT_CATEGORY_CHOICES = [
        ('Fast food', 'Fast food'), ('Organic', 'Organic'), ('Packaged', 'Packaged'), ('Beverages', 'Beverages'),
        ('Daily essentials', 'Daily essentials'),
        ('Casual wear', 'Casual wear'), ('Formal', 'Formal'), ('Ethnic', 'Ethnic'), ('Sportswear', 'Sportswear'),
        ('Smartphones', 'Smartphones'), ('Laptops', 'Laptops'), ('IoT', 'IoT'), ('Appliances', 'Appliances'),
        ('Two-wheelers', 'Two-wheelers'), ('EVs', 'EVs'), ('Cars', 'Cars'),
        ('Pharma', 'Pharma'), ('Wellness', 'Wellness'), ('Devices', 'Devices'),
        ('EdTech', 'EdTech'), ('Skill training', 'Skill training'),
        ('Solar panels', 'Solar panels'), ('Batteries', 'Batteries'),
        ('Real estate', 'Real estate'), ('Interiors', 'Interiors'),
        ('Insurance', 'Insurance'), ('Microfinance', 'Microfinance'), ('Credit', 'Credit'),
        ('Streaming', 'Streaming'), ('Gaming', 'Gaming'), ('Cinema', 'Cinema'),
        ('Other', 'Other'),
    ]

    SECTOR_CHOICES = [
        ('Retail', 'Retail'), ('Hospitality', 'Hospitality'), ('Fashion', 'Fashion'),
        ('Telecom', 'Telecom'), ('Manufacturing', 'Manufacturing'), ('Health', 'Health'),
        ('Education', 'Education'), ('Infrastructure', 'Infrastructure'), ('Construction', 'Construction'),
        ('Banking', 'Banking'), ('FinTech', 'FinTech'), ('Media', 'Media'), ('IT', 'IT'),
        ('Transport', 'Transport'), ('Other', 'Other'),
    ]

    AGE_GROUP_CHOICES = [
        ('18-24', '18-24'), ('25-34', '25-34'), ('35-44', '35-44'),
        ('45-54', '45-54'), ('55-64', '55-64'), ('65+', '65+'),
    ]

    GENDER_CHOICES = [
        ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other'),
    ]

    INCOME_RANGE_CHOICES = [
        ('Below 25k', 'Below 25k'), ('25k-50k', '25k-50k'), ('50k-100k', '50k-100k'),
        ('100k-200k', '100k-200k'), ('200k+', '200k+'),
    ]

    EDUCATION_LEVEL_CHOICES = [
        ('High School', 'High School'), ('Bachelors', 'Bachelors'), ('Masters', 'Masters'),
        ('PhD', 'PhD'), ('Other', 'Other'),
    ]

    LUXURY_LEVEL_CHOICES = [('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low'),]
    product_type = forms.ChoiceField(choices=PRODUCT_TYPE_CHOICES)
    product_luxury = forms.ChoiceField(choices=LUXURY_LEVEL_CHOICES)
    product_category = forms.ChoiceField(choices=PRODUCT_CATEGORY_CHOICES, required=False)
    sector = forms.ChoiceField(choices=SECTOR_CHOICES, required=False)
    age_group = forms.ChoiceField(choices=AGE_GROUP_CHOICES, required=False)
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)
    income_range = forms.ChoiceField(choices=INCOME_RANGE_CHOICES, required=False)
    education_level = forms.ChoiceField(choices=EDUCATION_LEVEL_CHOICES, required=False)
    price = forms.DecimalField(max_digits=10, decimal_places=2, required=False, help_text="Enter the product's price")

    # Define dependencies here for server-side validation
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

    def clean(self):
        cleaned = super().clean()
        product_type = cleaned.get('product_type')
        category = cleaned.get('product_category')
        sector = cleaned.get('sector')

        if product_type:
            deps = self.PRODUCT_DEPENDENCIES.get(product_type, {})
            allowed_categories = deps.get('categories', [])
            allowed_sectors = deps.get('sectors', [])

            if category and allowed_categories and category not in allowed_categories:
                self.add_error('product_category',
                    forms.ValidationError(f"Category '{category}' is not valid for product type '{product_type}'.")
                )

            if sector and allowed_sectors and sector not in allowed_sectors:
                self.add_error('sector',
                    forms.ValidationError(f"Sector '{sector}' is not valid for product type '{product_type}'.")
                )

        return cleaned

    class Meta:
        model = PredictionRequest
        fields = ['product_type', 'product_luxury', 'target_audience', 'price', 'region']
        # Exclude fields that will be derived or combined from new dropdowns
        exclude = ['target_audience', 'price']
