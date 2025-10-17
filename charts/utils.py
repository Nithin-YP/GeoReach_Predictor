import random
from datetime import datetime, timedelta
# from core.models import PredictionRequest  # Uncomment when ready to use real data

def get_entrepreneur_chart_data(user=None):
    """Generate chart data for entrepreneur dashboard"""
    
    # TODO: Replace with actual database queries when ready
    # if user:
    #     predictions = PredictionRequest.objects.filter(user=user)
    #     # Process predictions for charts
    
    # Bar Chart: Success by Category
    categories = ['Electronics', 'Fashion', 'Food', 'Services', 'Education']
    success_by_category = {
        'labels': categories,
        'data': [random.randint(60, 95) for _ in categories]
    }
    
    # Pie/Donut Chart: Success Level Distribution
    success_distribution = {
        'labels': ['High Potential', 'Medium Potential', 'Low Potential'],
        'data': [45, 35, 20],
        'colors': ['#28a745', '#ffc107', '#dc3545']
    }
    
    # Scatter Plot: Price vs Predicted Success
    scatter_data = [
        {'x': random.randint(100, 10000), 'y': random.randint(40, 95)} 
        for _ in range(20)
    ]
    
    # Line Chart: Trend Over Time (placeholder - last 7 days)
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    trend_data = {
        'labels': dates,
        'data': [random.randint(50, 90) for _ in dates]
    }

    # Radar Chart: Product Metrics
    radar_chart = {
        'labels': ['Speed', 'Quality', 'Cost', 'Time', 'Risk'],
        'data': [80, 70, 90, 85, 75]
    }
    
    # Bubble Chart: Investment vs Returns
    bubble_chart = {
        'data': [
            {'x': 100, 'y': 80, 'r': 10},
            {'x': 200, 'y': 60, 'r': 15},
            {'x': 150, 'y': 70, 'r': 12},
            {'x': 250, 'y': 85, 'r': 18}
        ],
        'xLabel': 'Investment',
        'yLabel': 'Returns'
    }

    return {
        'success_by_category': success_by_category,
        'success_distribution': success_distribution,
        'price_vs_success': scatter_data,
        'trend_over_time': trend_data,
        'radar_chart': radar_chart,
        'bubble_chart': bubble_chart

    }

def get_admin_chart_data(date_range=None):
    """Generate chart data for admin dashboard"""
    
    # TODO: Replace with actual database queries when ready
    # if date_range:
    #     start_date, end_date = date_range
    #     predictions = PredictionRequest.objects.filter(
    #         request_timestamp__range=(start_date, end_date)
    #     )
    
    # Line Chart: Predictions Over Time
    days = 30
    dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days - 1, -1, -1)]
    predictions_trend = {
        'labels': dates,
        'data': [random.randint(10, 100) for _ in dates]
    }
    
    # Bar Chart: Top Queried States
    states = ['Maharashtra', 'Delhi', 'Karnataka', 'Tamil Nadu', 'Gujarat']
    top_states = {
        'labels': states,
        'data': [random.randint(50, 200) for _ in states]
    }
    
    # Pie Chart: Product Category Queries
    category_queries = {
        'labels': ['Electronics', 'Fashion', 'Food', 'Services', 'Education'],
        'data': [25, 20, 18, 22, 15],
        'colors': ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8']
    }
    
    # Placeholder: Model Accuracy Over Versions
    model_accuracy = {
        'labels': ['v1.0', 'v1.1', 'v1.2', 'v1.3', 'v2.0'],
        'data': [75, 78, 82, 85, 88]
    }
    
    return {
        'predictions_trend': predictions_trend,
        'top_states': top_states,
        'category_queries': category_queries,
        'model_accuracy': model_accuracy
    }