from django.shortcuts import render
from .utils import get_map_clusters

def map_view(request, context=None):
    if context is None:
        context = {}
    context["clusters"] = get_map_clusters()
    return render(request, "geo/map.html", context)