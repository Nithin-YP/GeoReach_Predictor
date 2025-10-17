from django.shortcuts import render
from .utils import get_entrepreneur_chart_data, get_admin_chart_data
import json

def get_entrepreneur_charts_context():
    """Get chart data for entrepreneur dashboard"""
    chart_data = get_entrepreneur_chart_data()
    return {
        'entrepreneur_charts': json.dumps(chart_data)
    }

def get_admin_charts_context():
    """Get chart data for admin dashboard"""
    chart_data = get_admin_chart_data()
    return {
        'admin_charts': json.dumps(chart_data)
    }