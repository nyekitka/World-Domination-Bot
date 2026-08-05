from django.urls import path
from stats.views import render_stats

urlpatterns = [
    path('', render_stats)
]