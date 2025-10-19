from django.urls import path  # type: ignore
from django.views.generic import TemplateView
from . import views

app_name = 'core'

urlpatterns = [
    path('register/entrepreneur/', views.entrepreneur_register, name='entrepreneur_register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/entrepreneur/', views.entrepreneur_dashboard, name='entrepreneur_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/datasets/', views.dataset_management, name='dataset_management'),
    path('admin/users/', views.user_management, name='user_management'),
    # CSRF Test Page (for development/testing only)
    path('csrf-test/', TemplateView.as_view(template_name='csrf_test.html'), name='csrf_test'),
]