"""
Potential and Reachability Calculation Module

Calculates market potential and reachability scores based on database fields
similar to the approach in Queries_example.txt
"""

from decimal import Decimal
from django.db.models import Avg, Q
from geo.models import EconomicIndicator, DemographicProfile


def calculate_district_potential(district, state, product_category, target_age_group=None):
    """
    Calculate potential score (0-100) based on database fields
    
    Combines demographic, economic, and geographic factors specific to product category
    
    Strategy:
    1. If demographic/economic data available: Calculate from fields
    2. If missing data: Fallback to MarketPotentialZone.market_score (static dataset)
    
    Args:
        district: geo.models.District instance
        state: geo.models.State instance
        product_category: str - Product type (e.g., 'food', 'electronics', 'fashion')
        target_age_group: str - Optional target age (e.g., '25-34')
    
    Returns:
        float: Potential score 0-100
    """
    
    # Get latest economic data
    economic_data = EconomicIndicator.objects.filter(
        district=district
    ).order_by('-date_recorded').first()
    
    # Get demographic profiles
    demographic_query = DemographicProfile.objects.filter(district=district)
    if target_age_group:
        demographic_query = demographic_query.filter(age_group=target_age_group)
    
    # Calculate aggregates
    avg_disposable_income = demographic_query.aggregate(
        Avg('avg_disposable_income')
    )['avg_disposable_income__avg']
    
    # Check if we have sufficient data for calculation
    has_demographic_data = demographic_query.exists()
    has_economic_data = economic_data is not None
    
    # Fallback to MarketPotentialZone if insufficient data
    if not has_demographic_data and not has_economic_data:
        from geo.models import MarketPotentialZone
        mpz_score = MarketPotentialZone.objects.filter(
            district=district
        ).aggregate(Avg('market_score'))['market_score__avg']
        
        if mpz_score:
            return float(mpz_score)
        else:
            # No data at all - return baseline based on basic district info
            return calculate_baseline_potential(district)
    
    # Calculate population density
    population_density = 0
    if district.population and district.area_km2:
        population_density = float(district.population) / float(district.area_km2)
    
    # Get area type
    area_type = economic_data.area_type if economic_data else 'RURAL'
    
    # Product-category-specific scoring
    product_lower = product_category.lower() if product_category else 'generic'
    
    if any(keyword in product_lower for keyword in ['food', 'beverage', 'grocery', 'organic', 'restaurant']):
        score = calculate_food_potential(
            avg_disposable_income=avg_disposable_income,
            groceries_exp=demographic_query.aggregate(Avg('groceries_expenditure'))['groceries_expenditure__avg'],
            eating_out_exp=demographic_query.aggregate(Avg('eating_out_expenditure'))['eating_out_expenditure__avg'],
            area_type=area_type,
            population_density=population_density
        )
    
    elif any(keyword in product_lower for keyword in ['electronics', 'laptop', 'smartphone', 'gadget', 'iot', 'tech']):
        age_groups = list(demographic_query.values_list('age_group', flat=True).distinct())
        score = calculate_tech_potential(
            avg_disposable_income=avg_disposable_income,
            literacy_rate=district.literacy_rate,
            area_type=area_type,
            age_groups=age_groups,
            education_levels=list(demographic_query.values_list('education_level', flat=True).distinct())
        )
    
    elif any(keyword in product_lower for keyword in ['fashion', 'apparel', 'clothing', 'accessories']):
        age_groups = list(demographic_query.values_list('age_group', flat=True).distinct())
        score = calculate_fashion_potential(
            avg_disposable_income=avg_disposable_income,
            area_type=area_type,
            literacy_rate=district.literacy_rate,
            age_groups=age_groups
        )
    
    elif any(keyword in product_lower for keyword in ['healthcare', 'medical', 'wellness', 'fitness']):
        score = calculate_healthcare_potential(
            avg_disposable_income=avg_disposable_income,
            healthcare_exp=demographic_query.aggregate(Avg('healthcare_expenditure'))['healthcare_expenditure__avg'],
            literacy_rate=district.literacy_rate,
            population=district.population,
            age_groups=list(demographic_query.values_list('age_group', flat=True).distinct())
        )
    
    elif any(keyword in product_lower for keyword in ['education', 'training', 'course', 'learning']):
        score = calculate_education_potential(
            avg_disposable_income=avg_disposable_income,
            education_exp=demographic_query.aggregate(Avg('education_expenditure'))['education_expenditure__avg'],
            literacy_rate=district.literacy_rate,
            area_type=area_type,
            age_groups=list(demographic_query.values_list('age_group', flat=True).distinct())
        )
    
    else:
        # Generic potential calculation
        score = calculate_generic_potential(
            avg_disposable_income=avg_disposable_income,
            population=district.population,
            literacy_rate=district.literacy_rate,
            employment_rate=economic_data.employment_rate if economic_data else 50
        )
    
    return min(max(score, 0), 100)  # Clamp to 0-100


def calculate_food_potential(avg_disposable_income, groceries_exp, eating_out_exp, 
                             area_type, population_density):
    """Calculate potential for food/beverage products (0-100)"""
    score = 0
    
    # Income component (0-30 points)
    if avg_disposable_income:
        income_val = float(avg_disposable_income)
        if income_val > 50000:
            score += 30
        elif income_val > 35000:
            score += 25
        elif income_val > 25000:
            score += 20
        elif income_val > 15000:
            score += 10
        else:
            score += 5
    
    # Groceries expenditure (0-25 points)
    if groceries_exp:
        grocery_val = float(groceries_exp)
        if grocery_val > 8000:
            score += 25
        elif grocery_val > 6000:
            score += 20
        elif grocery_val > 4000:
            score += 15
        elif grocery_val > 2000:
            score += 10
        else:
            score += 5
    
    # Eating out expenditure (0-15 points)
    if eating_out_exp:
        eating_val = float(eating_out_exp)
        if eating_val > 5000:
            score += 15
        elif eating_val > 3000:
            score += 12
        elif eating_val > 1500:
            score += 8
        elif eating_val > 500:
            score += 5
    
    # Area type (0-15 points)
    if area_type == 'URBAN':
        score += 15
    elif area_type == 'COMBINED':
        score += 10
    else:  # RURAL
        score += 5
    
    # Population density (0-15 points)
    if population_density > 1000:
        score += 15
    elif population_density > 500:
        score += 12
    elif population_density > 200:
        score += 8
    elif population_density > 100:
        score += 5
    
    return score


def calculate_tech_potential(avg_disposable_income, literacy_rate, area_type, age_groups, education_levels):
    """Calculate potential for electronics/tech products (0-100)"""
    score = 0
    
    # Income component (0-35 points) - Higher weight for tech
    if avg_disposable_income:
        income_val = float(avg_disposable_income)
        if income_val > 60000:
            score += 35
        elif income_val > 45000:
            score += 30
        elif income_val > 35000:
            score += 25
        elif income_val > 25000:
            score += 18
        elif income_val > 20000:
            score += 10
        else:
            score += 5
    
    # Literacy rate as tech-adoption proxy (0-20 points)
    if literacy_rate:
        lit_val = float(literacy_rate)
        if lit_val > 90:
            score += 20
        elif lit_val > 85:
            score += 18
        elif lit_val > 80:
            score += 16
        elif lit_val > 75:
            score += 14
        elif lit_val > 70:
            score += 12
        elif lit_val > 60:
            score += 8
    
    # Age group match (0-20 points)
    tech_age_groups = ['18-24', '25-34', '35-44']
    matching_ages = [ag for ag in age_groups if ag in tech_age_groups]
    if len(matching_ages) >= 3:
        score += 20
    elif len(matching_ages) >= 2:
        score += 15
    elif len(matching_ages) >= 1:
        score += 10
    
    # Education level (0-15 points)
    if education_levels:
        high_edu = ['BACHELOR', 'MASTER', 'PHD']
        matching_edu = [edu for edu in education_levels if edu in high_edu]
        if len(matching_edu) >= 2:
            score += 15
        elif len(matching_edu) >= 1:
            score += 10
        else:
            score += 5
    
    # Area type (0-10 points) - Tech infrastructure
    if area_type == 'URBAN':
        score += 10
    elif area_type == 'COMBINED':
        score += 5
    
    return score


def calculate_fashion_potential(avg_disposable_income, area_type, literacy_rate, age_groups):
    """Calculate potential for fashion/apparel products (0-100)"""
    score = 0
    
    # Income sweet spot (0-35 points) - Mid-income focus
    if avg_disposable_income:
        income_val = float(avg_disposable_income)
        if 40000 <= income_val <= 70000:
            score += 35  # Sweet spot
        elif 30000 <= income_val < 40000:
            score += 30
        elif 25000 <= income_val < 30000:
            score += 25
        elif income_val > 70000:
            score += 30  # Premium segment
        elif income_val > 20000:
            score += 20
        else:
            score += 10
    
    # Young demographic (0-30 points)
    young_age_groups = ['18-24', '25-34']
    matching_ages = [ag for ag in age_groups if ag in young_age_groups]
    if len(matching_ages) >= 2:
        score += 30
    elif len(matching_ages) >= 1:
        score += 22
    
    # Urban presence (0-20 points) - Fashion accessibility
    if area_type == 'URBAN':
        score += 20
    elif area_type == 'COMBINED':
        score += 12
    
    # Literacy/Aspirational (0-15 points)
    if literacy_rate:
        lit_val = float(literacy_rate)
        if lit_val > 85:
            score += 15
        elif lit_val > 75:
            score += 12
        elif lit_val > 65:
            score += 8
        else:
            score += 5
    
    return score


def calculate_healthcare_potential(avg_disposable_income, healthcare_exp, literacy_rate, 
                                   population, age_groups):
    """Calculate potential for healthcare/wellness products (0-100)"""
    score = 0
    
    # Income component (0-25 points)
    if avg_disposable_income:
        income_val = float(avg_disposable_income)
        if income_val > 40000:
            score += 25
        elif income_val > 30000:
            score += 22
        elif income_val > 25000:
            score += 18
        elif income_val > 20000:
            score += 15
        else:
            score += 8
    
    # Healthcare expenditure (0-30 points)
    if healthcare_exp:
        health_val = float(healthcare_exp)
        if health_val > 5000:
            score += 30
        elif health_val > 3000:
            score += 25
        elif health_val > 2000:
            score += 20
        elif health_val > 1000:
            score += 15
        else:
            score += 8
    
    # Age group match (0-20 points) - Health-conscious ages
    health_age_groups = ['35-44', '45-54', '55+']
    matching_ages = [ag for ag in age_groups if ag in health_age_groups]
    if len(matching_ages) >= 3:
        score += 20
    elif len(matching_ages) >= 2:
        score += 16
    elif len(matching_ages) >= 1:
        score += 12
    
    # Literacy (0-15 points) - Health awareness
    if literacy_rate:
        lit_val = float(literacy_rate)
        if lit_val > 80:
            score += 15
        elif lit_val > 70:
            score += 12
        elif lit_val > 60:
            score += 8
    
    # Population (0-10 points) - Market size
    if population:
        pop_val = int(population)
        if pop_val > 1000000:
            score += 10
        elif pop_val > 500000:
            score += 8
        elif pop_val > 200000:
            score += 5
    
    return score


def calculate_education_potential(avg_disposable_income, education_exp, literacy_rate, 
                                  area_type, age_groups):
    """Calculate potential for education/training products (0-100)"""
    score = 0
    
    # Income component (0-25 points)
    if avg_disposable_income:
        income_val = float(avg_disposable_income)
        if income_val > 35000:
            score += 25
        elif income_val > 25000:
            score += 22
        elif income_val > 20000:
            score += 18
        elif income_val > 15000:
            score += 12
        else:
            score += 8
    
    # Education expenditure (0-30 points)
    if education_exp:
        edu_val = float(education_exp)
        if edu_val > 5000:
            score += 30
        elif edu_val > 3000:
            score += 25
        elif edu_val > 2000:
            score += 20
        elif edu_val > 1000:
            score += 15
        else:
            score += 8
    
    # Learning demographic (0-20 points)
    learning_age_groups = ['18-24', '25-34']
    matching_ages = [ag for ag in age_groups if ag in learning_age_groups]
    if len(matching_ages) >= 2:
        score += 20
    elif len(matching_ages) >= 1:
        score += 15
    
    # Literacy (0-15 points) - Education value
    if literacy_rate:
        lit_val = float(literacy_rate)
        if lit_val > 85:
            score += 15
        elif lit_val > 75:
            score += 12
        elif lit_val > 65:
            score += 8
    
    # Area type (0-10 points) - Access to education
    if area_type == 'URBAN':
        score += 10
    elif area_type == 'COMBINED':
        score += 7
    else:
        score += 3
    
    return score


def calculate_baseline_potential(district):
    """
    Returns a baseline potential score (float) based on basic district info.
    """
    score = 50  # Default baseline
    if district.population and district.area_km2:
        pop_density = float(district.population) / float(district.area_km2)
        if pop_density > 1000:
            score += 20
        elif pop_density > 500:
            score += 10
        elif pop_density > 200:
            score += 5
    if hasattr(district, 'literacy_rate') and district.literacy_rate:
        lit_val = float(district.literacy_rate)
        if lit_val > 80:
            score += 10
        elif lit_val > 60:
            score += 5
    return min(max(score, 0), 100)

def calculate_generic_potential(avg_disposable_income, population, literacy_rate, employment_rate):
    """Generic potential calculation for unclassified products (0-100)"""
    score = 0
    
    # Income (0-35 points)
    if avg_disposable_income:
        income_val = float(avg_disposable_income)
        if income_val > 50000:
            score += 35
        elif income_val > 35000:
            score += 30
        elif income_val > 25000:
            score += 25
        elif income_val > 15000:
            score += 18
        else:
            score += 10
    
    # Population (0-25 points)
    if population:
        pop_val = int(population)
        if pop_val > 2000000:
            score += 25
        elif pop_val > 1000000:
            score += 22
        elif pop_val > 500000:
            score += 18
        elif pop_val > 200000:
            score += 12
        else:
            score += 8
    
    # Literacy (0-20 points)
    if literacy_rate:
        lit_val = float(literacy_rate)
        if lit_val > 85:
            score += 20
        elif lit_val > 75:
            score += 16
        elif lit_val > 65:
            score += 12
        else:
            score += 8
    
    # Employment (0-20 points)
    if employment_rate:
        emp_val = float(employment_rate)
        if emp_val > 95:
            score += 20
        elif emp_val > 90:
            score += 16
        elif emp_val > 85:
            score += 12
        else:
            score += 8
    
    return score


def calculate_district_reachability(district, state, product_category, prediction):
    """
    Calculate reachability index (0-1) combining potential with accessibility
    
    Reachability = Potential × Accessibility × Demographic_Match
    
    Args:
        district: geo.models.District instance
        state: geo.models.State instance
        product_category: str
        prediction: core.models.PredictionRequest instance
    
    Returns:
        float: Reachability index 0-1
    """
    
    # 1. Base Potential (0-1 normalized)
    potential_score = calculate_district_potential(
        district, state, product_category,
        target_age_group=getattr(prediction, 'target_age_group', None)
    ) / 100.0
    
    # 2. Accessibility Factor (0-1)
    economic_data = EconomicIndicator.objects.filter(
        district=district
    ).order_by('-date_recorded').first()
    
    if economic_data:
        if economic_data.area_type == 'URBAN':
            accessibility = 1.0
        elif economic_data.area_type == 'COMBINED':
            accessibility = 0.75
        else:  # RURAL
            accessibility = 0.45
    else:
        accessibility = 0.6  # Default moderate
    
    # 3. Demographic Match (0-1)
    demographic_match = calculate_demographic_match(
        district=district,
        target_age=getattr(prediction, 'target_age_group', None),
        target_income=getattr(prediction, 'target_income_range', None)
    )
    
    # Combined Reachability
    reachability = potential_score * accessibility * demographic_match
    
    return min(max(reachability, 0), 1)  # Clamp to 0-1


def calculate_demographic_match(district, target_age, target_income):
    """
    Calculate how well district demographics match target profile (0-1)
    """
    matches = []
    
    # Age group match
    if target_age:
        age_profiles = DemographicProfile.objects.filter(
            district=district,
            age_group=target_age
        )
        if age_profiles.exists():
            matches.append(1.0)
        else:
            # Check adjacent age groups
            adjacent = get_adjacent_age_groups(target_age)
            adjacent_match = DemographicProfile.objects.filter(
                district=district,
                age_group__in=adjacent
            ).exists()
            matches.append(0.7 if adjacent_match else 0.3)
    
    # Income match
    if target_income:
        income_profiles = DemographicProfile.objects.filter(district=district)
        avg_income = income_profiles.aggregate(
            Avg('avg_disposable_income')
        )['avg_disposable_income__avg']
        
        if avg_income:
            income_match = calculate_income_match(float(avg_income), target_income)
            matches.append(income_match)
    
    # Average of all matches
    return sum(matches) / len(matches) if matches else 0.6  # Default moderate match


def get_adjacent_age_groups(age_group):
    """Get adjacent age groups for partial matching"""
    age_sequence = ['18-24', '25-34', '35-44', '45-54', '55+']
    try:
        idx = age_sequence.index(age_group)
        adjacent = []
        if idx > 0:
            adjacent.append(age_sequence[idx - 1])
        if idx < len(age_sequence) - 1:
            adjacent.append(age_sequence[idx + 1])
        return adjacent
    except ValueError:
        return []


def calculate_income_match(avg_income, target_income_range):
    """
    Calculate how well average income matches target range (0-1)
    
    Args:
        avg_income: float - Average disposable income
        target_income_range: str - e.g., '<5L', '5L-10L', '10L-20L', '>20L'
    """
    # Parse target income range
    if target_income_range == '<5L' or target_income_range == 'Below 5L':
        target_min, target_max = 0, 50000
    elif target_income_range == '5L-10L' or target_income_range == '5-10L':
        target_min, target_max = 50000, 100000
    elif target_income_range == '10L-20L' or target_income_range == '10-20L':
        target_min, target_max = 100000, 200000
    elif target_income_range == '>20L' or target_income_range == 'Above 20L':
        target_min, target_max = 200000, float('inf')
    else:
        return 0.5  # Unknown range, moderate match
    
    # Check if income falls in range
    if target_min <= avg_income <= target_max:
        return 1.0  # Perfect match
    elif target_min * 0.8 <= avg_income <= target_max * 1.2:
        return 0.8  # Close match (within 20%)
    elif target_min * 0.5 <= avg_income <= target_max * 1.5:
        return 0.6  # Moderate match (within 50%)
    else:
        return 0.3  # Poor match
