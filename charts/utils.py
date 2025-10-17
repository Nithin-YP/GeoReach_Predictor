import random
from datetime import datetime, timedelta
from django.db import connection

def execute_query(query, params=None):
    """Execute a raw SQL query and return results as list of dicts."""
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_entrepreneur_chart_data(user=None):
    """Generate chart data for entrepreneur dashboard using real database data"""
    
    # ========================================
    # Bar Chart: Top States by Employment (normalized to percentage)
    # ========================================
    query = """
        SELECT state_name, 
               ROUND((est_employed::numeric / population::numeric * 100), 2) as employment_rate
        FROM states 
        WHERE est_employed IS NOT NULL 
        AND population IS NOT NULL
        AND population > 0
        ORDER BY employment_rate DESC 
        LIMIT 10
    """
    top_states = execute_query(query)
    success_by_category = {
        'labels': [row['state_name'] for row in top_states],
        'data': [float(row['employment_rate']) for row in top_states]
    }
    
    # ========================================
    # Pie/Donut Chart: Area Type Distribution
    # ========================================
    query = """
        SELECT area_type, COUNT(*) as count 
        FROM states 
        WHERE area_type IS NOT NULL 
        GROUP BY area_type
    """
    area_distribution = execute_query(query)
    success_distribution = {
        'labels': [row['area_type'] for row in area_distribution],
        'data': [int(row['count']) for row in area_distribution],
        'colors': ['#28a745', '#ffc107', '#dc3545']
    }
    
    # ========================================
    # Scatter Plot: Population (in millions) vs Unemployment
    # ========================================
    query = """
        SELECT ROUND((population::numeric / 1000000), 2) as population_millions, 
               est_unemployment_rate 
        FROM states 
        WHERE population IS NOT NULL 
        AND est_unemployment_rate IS NOT NULL 
        LIMIT 30
    """
    scatter_rows = execute_query(query)
    scatter_data = [
        {'x': float(row['population_millions']), 'y': float(row['est_unemployment_rate'])} 
        for row in scatter_rows
    ]
    
    # ========================================
    # Line Chart: Customer Spending Trend (by age groups, scaled down)
    # ========================================
    query = """
        SELECT age, ROUND(AVG(spending)::numeric / 1000, 2) as avg_spending_thousands
        FROM customers 
        WHERE age IS NOT NULL AND spending IS NOT NULL 
        GROUP BY age 
        ORDER BY age 
        LIMIT 10
    """
    trend_rows = execute_query(query)
    trend_data = {
        'labels': [str(row['age']) for row in trend_rows],
        'data': [float(row['avg_spending_thousands']) for row in trend_rows]
    }
    
    # ========================================
    # Radar Chart: Average Expenditure Categories (scaled to 0-100)
    # ========================================
    query = """
        SELECT 
            AVG(groceries_exp) as groceries,
            AVG(transport_exp) as transport,
            AVG(eating_out_exp) as eating_out,
            AVG(entertainment_exp) as entertainment,
            AVG(utilities_exp) as utilities
        FROM expenditures
        WHERE groceries_exp IS NOT NULL
    """
    radar_row = execute_query(query)
    if radar_row and radar_row[0]['groceries'] is not None:
        # Get max value to normalize to 0-100 scale
        values = [
            float(radar_row[0]['groceries'] or 0),
            float(radar_row[0]['transport'] or 0),
            float(radar_row[0]['eating_out'] or 0),
            float(radar_row[0]['entertainment'] or 0),
            float(radar_row[0]['utilities'] or 0)
        ]
        max_val = max(values) if max(values) > 0 else 1
        
        radar_chart = {
            'labels': ['Groceries', 'Transport', 'Eating Out', 'Entertainment', 'Utilities'],
            'data': [round((v / max_val) * 100, 2) for v in values]  # Normalize to 0-100
        }
    else:
        radar_chart = {
            'labels': ['Groceries', 'Transport', 'Eating Out', 'Entertainment', 'Utilities'],
            'data': [20, 15, 10, 12, 18]  # Placeholder if no data
        }
    
    # ========================================
    # Bubble Chart: Income vs Spending (scaled appropriately)
    # ========================================
    query = """
        SELECT ROUND(income::numeric / 1000, 2) as income_thousands,
               ROUND(spending::numeric / 1000, 2) as spending_thousands,
               purchase_frequency 
        FROM customers 
        WHERE income IS NOT NULL 
        AND spending IS NOT NULL 
        AND purchase_frequency IS NOT NULL 
        LIMIT 20
    """
    bubble_rows = execute_query(query)
    bubble_chart = {
        'data': [
            {
                'x': float(row['income_thousands']),
                'y': float(row['spending_thousands']),
                'r': float(row['purchase_frequency']) * 10  # Scale for visibility
            }
            for row in bubble_rows
        ],
        'xLabel': 'Income (thousands)',
        'yLabel': 'Spending (thousands)'
    }
    
    return {
        'success_by_category': success_by_category,
        'success_distribution': success_distribution,
        'price_vs_success': scatter_data,
        'trend_over_time': trend_data,
        'radar_chart': radar_chart,
        'bubble_chart': bubble_chart
    }

def get_admin_chart_data():
    """Generate chart data for admin dashboard using real database data"""
    
    # ========================================
    # Line Chart: Employment by Industry
    # ========================================
    query = """
        SELECT industry, COUNT(*) as count 
        FROM employment 
        WHERE industry IS NOT NULL 
        GROUP BY industry 
        ORDER BY count DESC 
        LIMIT 10
    """
    industry_rows = execute_query(query)
    predictions_trend = {
        'labels': [row['industry'] for row in industry_rows],
        'data': [int(row['count']) for row in industry_rows]
    }
    
    # ========================================
    # Bar Chart: Top Districts by Population (in millions)
    # ========================================
    query = """
        SELECT district_name, 
               ROUND((population_district::numeric / 1000000), 2) as population_millions
        FROM districts 
        WHERE population_district IS NOT NULL 
        ORDER BY population_millions DESC 
        LIMIT 10
    """
    district_rows = execute_query(query)
    top_states = {
        'labels': [row['district_name'] for row in district_rows],
        'data': [float(row['population_millions']) for row in district_rows]
    }
    
    # ========================================
    # Pie Chart: Employment Status Distribution
    # ========================================
    query = """
        SELECT employment_status, COUNT(*) as count 
        FROM employment 
        WHERE employment_status IS NOT NULL 
        GROUP BY employment_status
    """
    emp_status = execute_query(query)
    category_queries = {
        'labels': [row['employment_status'] for row in emp_status],
        'data': [int(row['count']) for row in emp_status],
        'colors': ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8']
    }
    
    # ========================================
    # Line Chart: Average Salary by Education Level (in thousands)
    # ========================================
    query = """
        SELECT education_level, 
               ROUND(AVG(monthly_salary_inr)::numeric / 1000, 2) as avg_salary_thousands
        FROM employment 
        WHERE education_level IS NOT NULL 
        AND monthly_salary_inr IS NOT NULL 
        GROUP BY education_level 
        ORDER BY avg_salary_thousands DESC
    """
    salary_rows = execute_query(query)
    model_accuracy = {
        'labels': [row['education_level'] for row in salary_rows],
        'data': [float(row['avg_salary_thousands']) for row in salary_rows]
    }
    
    return {
        'predictions_trend': predictions_trend,
        'top_states': top_states,
        'category_queries': category_queries,
        'model_accuracy': model_accuracy
    }