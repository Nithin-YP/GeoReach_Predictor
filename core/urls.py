from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('register/entrepreneur/', views.entrepreneur_register, name='entrepreneur_register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/entrepreneur/', views.entrepreneur_dashboard, name='entrepreneur_dashboard'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
]