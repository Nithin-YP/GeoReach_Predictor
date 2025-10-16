"""
URL configuration for georeach_predictor project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin  # type: ignore
from django.urls import path, include  # type: ignore
from django.shortcuts import redirect  # type: ignore

def home_redirect(request):
    """Redirect to login page"""
    return redirect('core:login')

urlpatterns = [
    path('', home_redirect, name='home'),
    path("admin/", admin.site.urls),
    path('core/', include('core.urls')),
    path("geo/", include("geo.urls")),
]
